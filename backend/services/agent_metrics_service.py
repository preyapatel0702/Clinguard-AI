"""
agent_metrics_service.py
------------------------
Track per-agent execution statistics in a thread-safe, persistent manner.

Agents register themselves implicitly the first time they emit a metric —
no code changes are needed when new agents are added to the pipeline.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_AGENT_METRICS_PATH = Path("data/analytics/agent_metrics.json")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class AgentMetrics:
    """Statistics maintained for a single agent."""

    agent_name: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time_ms: float = 0.0
    minimum_latency_ms: Optional[float] = None
    maximum_latency_ms: Optional[float] = None
    last_execution_time: Optional[str] = None  # ISO-8601

    @property
    def success_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    @property
    def failure_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.failure_count / self.execution_count

    @property
    def average_latency_ms(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.total_execution_time_ms / self.execution_count

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["success_rate"] = round(self.success_rate, 4)
        d["failure_rate"] = round(self.failure_rate, 4)
        d["average_latency_ms"] = round(self.average_latency_ms, 3)
        if d["minimum_latency_ms"] is not None:
            d["minimum_latency_ms"] = round(d["minimum_latency_ms"], 3)
        if d["maximum_latency_ms"] is not None:
            d["maximum_latency_ms"] = round(d["maximum_latency_ms"], 3)
        return d


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AgentMetricsService:
    """
    Persist and serve per-agent execution metrics.

    Agents auto-register on first use; new agents require no code changes.

    Parameters
    ----------
    storage_path:
        JSON file path for persisted metrics.
    """

    def __init__(self, storage_path: Path = DEFAULT_AGENT_METRICS_PATH) -> None:
        self._path = Path(storage_path)
        self._lock = threading.Lock()
        self._agents: Dict[str, AgentMetrics] = {}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()
        logger.info("AgentMetricsService initialised | storage=%s", self._path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_execution(
        self,
        agent_name: str,
        latency_ms: float,
        success: bool,
        execution_time: Optional[str] = None,
    ) -> None:
        """
        Record one agent execution (thread-safe).

        Parameters
        ----------
        agent_name:
            Unique identifier for the agent (e.g. ``"RiskScoringAgent"``).
        latency_ms:
            Wall-clock execution time in milliseconds.
        success:
            Whether the agent completed without error.
        execution_time:
            ISO-8601 timestamp of execution (defaults to now).
        """
        from datetime import datetime, timezone

        if execution_time is None:
            execution_time = datetime.now(timezone.utc).isoformat()

        with self._lock:
            if agent_name not in self._agents:
                self._agents[agent_name] = AgentMetrics(agent_name=agent_name)
            m = self._agents[agent_name]
            m.execution_count += 1
            if success:
                m.success_count += 1
            else:
                m.failure_count += 1
            m.total_execution_time_ms += latency_ms
            m.minimum_latency_ms = (
                min(m.minimum_latency_ms, latency_ms)
                if m.minimum_latency_ms is not None
                else latency_ms
            )
            m.maximum_latency_ms = (
                max(m.maximum_latency_ms, latency_ms)
                if m.maximum_latency_ms is not None
                else latency_ms
            )
            m.last_execution_time = execution_time
            self._save()

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Return all agent metrics as plain dicts."""
        with self._lock:
            return {name: m.to_dict() for name, m in self._agents.items()}

    def get_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Return metrics for a specific agent, or None if not seen."""
        with self._lock:
            m = self._agents.get(agent_name)
            return m.to_dict() if m else None

    def reset(self) -> None:
        """Clear all agent metrics (useful for testing)."""
        with self._lock:
            self._agents = {}
            self._save()
        logger.warning("AgentMetricsService reset")

    # ------------------------------------------------------------------
    # Context manager for automatic timing
    # ------------------------------------------------------------------

    class _AgentTimer:
        """Context manager that records a single agent execution."""

        def __init__(self, service: "AgentMetricsService", agent_name: str) -> None:
            self._svc = service
            self._name = agent_name
            self._start: float = 0.0
            self._success = True

        def __enter__(self) -> "_AgentTimer":
            self._start = time.perf_counter()
            return self

        def fail(self) -> None:
            self._success = False

        def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
            elapsed_ms = (time.perf_counter() - self._start) * 1000
            if exc_type is not None:
                self._success = False
            self._svc.record_execution(self._name, elapsed_ms, self._success)
            return False  # do not suppress exceptions

    def timer(self, agent_name: str) -> "_AgentTimer":
        """Return a context manager that automatically records execution."""
        return self._AgentTimer(self, agent_name)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text())
                for name, data in raw.items():
                    # Remove derived properties that are not __init__ params
                    data.pop("success_rate", None)
                    data.pop("failure_rate", None)
                    data.pop("average_latency_ms", None)
                    self._agents[name] = AgentMetrics(**data)
                logger.debug(
                    "Loaded metrics for %d agents from %s",
                    len(self._agents),
                    self._path,
                )
        except Exception as exc:
            logger.warning("Could not load agent metrics (%s); starting fresh", exc)

    def _save(self) -> None:
        try:
            payload = {name: m.to_dict() for name, m in self._agents.items()}
            self._path.write_text(json.dumps(payload, indent=2))
        except Exception as exc:
            logger.error("Failed to persist agent metrics: %s", exc)
