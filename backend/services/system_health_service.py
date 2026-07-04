"""
system_health_service.py
------------------------
Structured health reporting for ClinGuard-AI Phase 10.

Checks every major subsystem and returns machine-readable health reports
suitable for consumption by monitoring dashboards, load balancers, or
Kubernetes liveness/readiness probes.
"""

from __future__ import annotations

import logging
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil  # optional — gracefully degraded if unavailable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ComponentHealth:
    component: str
    status: HealthStatus
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "details": self.details,
            "errors": self.errors,
            "recommendations": self.recommendations,
        }


@dataclass
class SystemHealthReport:
    overall_status: HealthStatus
    timestamp: str
    components: List[ComponentHealth] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "timestamp": self.timestamp,
            "components": [c.to_dict() for c in self.components],
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SystemHealthService:
    """
    Collects and reports health information for ClinGuard-AI subsystems.

    Parameters
    ----------
    analytics_service:
        AnalyticsService instance (tested for storage health).
    agent_metrics_service:
        AgentMetricsService instance (tested for persistence layer health).
    data_dir:
        Root directory for data files (tested for writability).
    ml_model_paths:
        Optional list of model file paths to probe for availability.
    """

    def __init__(
        self,
        analytics_service=None,
        agent_metrics_service=None,
        data_dir: Path = Path("data"),
        ml_model_paths: Optional[List[Path]] = None,
    ) -> None:
        self._analytics_svc = analytics_service
        self._agent_svc = agent_metrics_service
        self._data_dir = Path(data_dir)
        self._ml_model_paths = ml_model_paths or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_full_health(self) -> SystemHealthReport:
        """Return a complete health report for all subsystems."""
        components = [
            self.check_pipeline(),
            self.check_storage(),
            self.check_models(),
            self.check_system(),
        ]
        overall = self._aggregate_status([c.status for c in components])
        return SystemHealthReport(
            overall_status=overall,
            timestamp=self._now(),
            components=components,
        )

    def check_pipeline(self) -> ComponentHealth:
        """Check whether the analytics pipeline is operational."""
        ts = self._now()
        errors: List[str] = []
        details: Dict[str, Any] = {}
        recommendations: List[str] = []

        if self._analytics_svc is not None:
            try:
                overview = self._analytics_svc.get_overview()
                details["total_requests"] = overview.get("total_requests", 0)
                details["average_latency_ms"] = overview.get("average_latency_ms")
                details["average_risk_score"] = overview.get("average_risk_score")
            except Exception as exc:
                errors.append(f"AnalyticsService.get_overview failed: {exc}")
        else:
            details["note"] = "No analytics service bound"

        status = HealthStatus.UNHEALTHY if errors else HealthStatus.HEALTHY
        return ComponentHealth(
            component="pipeline",
            status=status,
            timestamp=ts,
            details=details,
            errors=errors,
            recommendations=recommendations,
        )

    def check_storage(self) -> ComponentHealth:
        """Check persistence layer writability."""
        ts = self._now()
        errors: List[str] = []
        details: Dict[str, Any] = {}
        recommendations: List[str] = []

        # Check analytics storage
        if self._analytics_svc is not None:
            try:
                healthy = self._analytics_svc.storage_healthy()
                details["analytics_storage_writable"] = healthy
                if not healthy:
                    errors.append("Analytics storage directory is not writable")
                    recommendations.append("Check filesystem permissions on data/analytics/")
            except Exception as exc:
                errors.append(f"Analytics storage probe failed: {exc}")
        else:
            details["analytics_storage"] = "no service bound"

        # Check agent metrics persistence
        if self._agent_svc is not None:
            try:
                path = self._agent_svc._path
                details["agent_metrics_path"] = str(path)
                details["agent_metrics_exists"] = path.exists()
            except Exception as exc:
                errors.append(f"Agent metrics storage probe failed: {exc}")

        # General data dir
        try:
            details["data_dir"] = str(self._data_dir)
            details["data_dir_exists"] = self._data_dir.exists()
            probe = self._data_dir / ".health_probe"
            probe.parent.mkdir(parents=True, exist_ok=True)
            probe.write_text("ok")
            probe.unlink()
            details["data_dir_writable"] = True
        except Exception as exc:
            details["data_dir_writable"] = False
            errors.append(f"Data directory not writable: {exc}")
            recommendations.append("Ensure the process has write access to the data/ directory")

        status = HealthStatus.UNHEALTHY if errors else HealthStatus.HEALTHY
        return ComponentHealth(
            component="storage",
            status=status,
            timestamp=ts,
            details=details,
            errors=errors,
            recommendations=recommendations,
        )

    def check_models(self) -> ComponentHealth:
        """Check ML model file availability."""
        ts = self._now()
        errors: List[str] = []
        details: Dict[str, Any] = {}
        recommendations: List[str] = []

        if not self._ml_model_paths:
            details["note"] = "No model paths configured"
            return ComponentHealth(
                component="models",
                status=HealthStatus.HEALTHY,
                timestamp=ts,
                details=details,
                errors=errors,
                recommendations=["Configure ml_model_paths in SystemHealthService for model probing"],
            )

        available = []
        missing = []
        for p in self._ml_model_paths:
            path = Path(p)
            if path.exists():
                available.append(str(path))
            else:
                missing.append(str(path))

        details["available"] = available
        details["missing"] = missing
        details["total_configured"] = len(self._ml_model_paths)

        if missing:
            errors.extend([f"Model file not found: {m}" for m in missing])
            recommendations.append("Ensure all model files are present before starting the service")

        status = HealthStatus.UNHEALTHY if missing else HealthStatus.HEALTHY
        return ComponentHealth(
            component="models",
            status=status,
            timestamp=ts,
            details=details,
            errors=errors,
            recommendations=recommendations,
        )

    def check_system(self) -> ComponentHealth:
        """Check overall system resource health (CPU, memory, disk)."""
        ts = self._now()
        errors: List[str] = []
        details: Dict[str, Any] = {}
        recommendations: List[str] = []

        details["python_version"] = platform.python_version()
        details["platform"] = platform.system()

        try:
            mem = psutil.virtual_memory()
            details["memory_total_mb"] = round(mem.total / (1024 ** 2), 1)
            details["memory_available_mb"] = round(mem.available / (1024 ** 2), 1)
            details["memory_percent_used"] = mem.percent
            if mem.percent > 90:
                errors.append(f"Memory usage critical: {mem.percent}%")
                recommendations.append("Investigate memory-intensive processes")
            elif mem.percent > 75:
                recommendations.append("Memory usage elevated; monitor closely")

            cpu = psutil.cpu_percent(interval=0.1)
            details["cpu_percent"] = cpu
            if cpu > 90:
                recommendations.append("CPU usage very high; consider scaling")

            disk = psutil.disk_usage(str(self._data_dir.parent))
            details["disk_free_gb"] = round(disk.free / (1024 ** 3), 2)
            details["disk_percent_used"] = disk.percent
            if disk.percent > 90:
                errors.append(f"Disk usage critical: {disk.percent}%")
                recommendations.append("Free disk space urgently")

        except ImportError:
            details["psutil"] = "not installed — install psutil for system metrics"
        except Exception as exc:
            logger.debug("psutil probe error: %s", exc)
            details["psutil_error"] = str(exc)

        status = HealthStatus.DEGRADED if (recommendations and not errors) else (
            HealthStatus.UNHEALTHY if errors else HealthStatus.HEALTHY
        )
        return ComponentHealth(
            component="system",
            status=status,
            timestamp=ts,
            details=details,
            errors=errors,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _aggregate_status(statuses: List[HealthStatus]) -> HealthStatus:
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN
