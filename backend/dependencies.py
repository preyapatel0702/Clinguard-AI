"""
dependencies.py
---------------
FastAPI dependency injection for Phase 10 services.

Provides singleton accessors for all Phase 10 services so FastAPI route
handlers receive fully-configured instances via ``Depends()``.

Usage in a router::

    from backend.dependencies import get_analytics, get_health
    
    @router.get("/metrics/overview")
    def overview(svc: AnalyticsService = Depends(get_analytics)):
        return svc.get_overview()
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from backend.services.agent_metrics_service import AgentMetricsService
from backend.services.analytics_service import AnalyticsService
from backend.services.metrics_aggregator import MetricsAggregator
from backend.services.system_health_service import SystemHealthService
from backend.middleware.observability import Tracer


# ---------------------------------------------------------------------------
# Singleton factories (lru_cache ensures one instance per process)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_analytics() -> AnalyticsService:
    """Return the application-wide AnalyticsService singleton."""
    return AnalyticsService()


@lru_cache(maxsize=1)
def get_agent_metrics() -> AgentMetricsService:
    """Return the application-wide AgentMetricsService singleton."""
    return AgentMetricsService()


@lru_cache(maxsize=1)
def get_metrics_aggregator() -> MetricsAggregator:
    """Return the application-wide MetricsAggregator singleton."""
    return MetricsAggregator(analytics_service=get_analytics())


@lru_cache(maxsize=1)
def get_health_service() -> SystemHealthService:
    """Return the application-wide SystemHealthService singleton."""
    return SystemHealthService(
        analytics_service=get_analytics(),
        agent_metrics_service=get_agent_metrics(),
        data_dir=Path("data"),
    )


@lru_cache(maxsize=1)
def get_tracer() -> Tracer:
    """Return the application-wide Tracer singleton."""
    return Tracer()
