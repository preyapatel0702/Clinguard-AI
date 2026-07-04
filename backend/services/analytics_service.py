"""
analytics_service.py
--------------------
Persistent, thread-safe analytics collection for ClinGuard-AI Phase 10.

Tracks aggregate platform statistics and a rolling window of historical
records that feeds the metrics aggregator.  All public methods are safe to
call from concurrent request handlers.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Storage path (override via env or constructor)
# ---------------------------------------------------------------------------
DEFAULT_STORAGE_PATH = Path("data/analytics/analytics_state.json")
DEFAULT_HISTORY_PATH = Path("data/analytics/analytics_history.json")
DEFAULT_RETENTION_DAYS = 90


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class AnalyticsSnapshot:
    """Immutable snapshot recorded after every pipeline execution."""

    timestamp: str  # ISO-8601 UTC
    latency_ms: float
    risk_score: float
    hallucination_detected: bool
    validation_success: bool
    alerts_generated: int
    high_risk: bool
    pipeline_execution_time_ms: float
    correlation_id: str = ""


@dataclass
class AggregateStats:
    """Running aggregate counters persisted between restarts."""

    total_requests: int = 0
    total_latency_ms: float = 0.0
    total_risk_score: float = 0.0
    total_hallucinations: int = 0
    total_validation_success: int = 0
    total_alerts_generated: int = 0
    total_high_risk_cases: int = 0
    total_pipeline_execution_time_ms: float = 0.0

    # Derived helpers (not persisted, recomputed on load)
    @property
    def average_latency(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests

    @property
    def average_risk_score(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_risk_score / self.total_requests

    @property
    def hallucination_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_hallucinations / self.total_requests

    @property
    def validation_success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_validation_success / self.total_requests

    @property
    def average_pipeline_execution_time(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_pipeline_execution_time_ms / self.total_requests


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AnalyticsService:
    """
    Thread-safe analytics service for ClinGuard-AI.

    Persists aggregate counters and a rolling history of individual
    AnalyticsSnapshots.  Exposes simple record/query methods used by
    the analytics middleware and metrics endpoints.

    Parameters
    ----------
    storage_path:
        Path for the JSON file that stores aggregate counters.
    history_path:
        Path for the JSON file that stores historical snapshots.
    retention_days:
        How many days of snapshot history to keep.
    """

    def __init__(
        self,
        storage_path: Path = DEFAULT_STORAGE_PATH,
        history_path: Path = DEFAULT_HISTORY_PATH,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        self._storage_path = Path(storage_path)
        self._history_path = Path(history_path)
        self._retention_days = retention_days
        self._lock = threading.Lock()
        self._stats = AggregateStats()
        self._history: List[AnalyticsSnapshot] = []

        self._ensure_dirs()
        self._load()
        logger.info(
            "AnalyticsService initialised | storage=%s | history=%s",
            self._storage_path,
            self._history_path,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, snapshot: AnalyticsSnapshot) -> None:
        """Record a single pipeline execution snapshot (thread-safe)."""
        with self._lock:
            self._update_stats(snapshot)
            self._history.append(snapshot)
            self._prune_history()
            self._save()

    def get_overview(self) -> Dict[str, Any]:
        """Return aggregate overview metrics."""
        with self._lock:
            s = self._stats
            return {
                "total_requests": s.total_requests,
                "average_latency_ms": round(s.average_latency, 3),
                "average_risk_score": round(s.average_risk_score, 4),
                "hallucination_rate": round(s.hallucination_rate, 4),
                "validation_success_rate": round(s.validation_success_rate, 4),
                "alerts_generated": s.total_alerts_generated,
                "high_risk_cases": s.total_high_risk_cases,
                "average_pipeline_execution_time_ms": round(
                    s.average_pipeline_execution_time, 3
                ),
            }

    def get_history(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[AnalyticsSnapshot]:
        """Return snapshots optionally filtered by time window."""
        with self._lock:
            result = list(self._history)

        if since:
            result = [s for s in result if datetime.fromisoformat(s.timestamp) >= since]
        if until:
            result = [s for s in result if datetime.fromisoformat(s.timestamp) <= until]
        return result

    def get_stats(self) -> AggregateStats:
        """Return a copy of current aggregate stats."""
        with self._lock:
            import copy
            return copy.deepcopy(self._stats)

    def reset(self) -> None:
        """Reset all counters and history (useful for testing)."""
        with self._lock:
            self._stats = AggregateStats()
            self._history = []
            self._save()
        logger.warning("AnalyticsService reset — all data cleared")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_stats(self, s: AnalyticsSnapshot) -> None:
        st = self._stats
        st.total_requests += 1
        st.total_latency_ms += s.latency_ms
        st.total_risk_score += s.risk_score
        st.total_hallucinations += int(s.hallucination_detected)
        st.total_validation_success += int(s.validation_success)
        st.total_alerts_generated += s.alerts_generated
        st.total_high_risk_cases += int(s.high_risk)
        st.total_pipeline_execution_time_ms += s.pipeline_execution_time_ms

    def _prune_history(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        self._history = [
            h
            for h in self._history
            if datetime.fromisoformat(h.timestamp).replace(tzinfo=timezone.utc) >= cutoff
        ]

    def _ensure_dirs(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._history_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        self._load_stats()
        self._load_history()

    def _load_stats(self) -> None:
        try:
            if self._storage_path.exists():
                raw = json.loads(self._storage_path.read_text())
                self._stats = AggregateStats(**raw)
                logger.debug("Loaded aggregate stats from %s", self._storage_path)
        except Exception as exc:
            logger.warning("Could not load aggregate stats (%s); starting fresh", exc)
            self._stats = AggregateStats()

    def _load_history(self) -> None:
        try:
            if self._history_path.exists():
                raw = json.loads(self._history_path.read_text())
                self._history = [AnalyticsSnapshot(**item) for item in raw]
                logger.debug(
                    "Loaded %d history records from %s",
                    len(self._history),
                    self._history_path,
                )
        except Exception as exc:
            logger.warning("Could not load history (%s); starting fresh", exc)
            self._history = []

    def _save(self) -> None:
        try:
            self._storage_path.write_text(
                json.dumps(asdict(self._stats), indent=2)
            )
            self._history_path.write_text(
                json.dumps([asdict(h) for h in self._history], indent=2)
            )
        except Exception as exc:
            logger.error("Failed to persist analytics: %s", exc)

    # ------------------------------------------------------------------
    # Storage health probe
    # ------------------------------------------------------------------

    def storage_healthy(self) -> bool:
        """Return True if storage directories are writable."""
        try:
            probe = self._storage_path.parent / ".probe"
            probe.write_text("ok")
            probe.unlink()
            return True
        except Exception:
            return False
