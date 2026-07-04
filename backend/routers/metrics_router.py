"""
metrics_router.py
-----------------
FastAPI router for all Phase 10 /metrics/* endpoints.

Endpoints
---------
GET /metrics/overview        — aggregate platform statistics
GET /metrics/risk-trends     — hourly/daily/weekly/monthly risk stats
GET /metrics/hallucinations  — hallucination analytics
GET /metrics/validations     — validation analytics
GET /metrics/performance     — latency and execution metrics
GET /metrics/agents          — per-agent execution metrics
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends

from backend.dependencies import (
    get_agent_metrics,
    get_analytics,
    get_metrics_aggregator,
)
from backend.services.agent_metrics_service import AgentMetricsService
from backend.services.analytics_service import AnalyticsService
from backend.services.metrics_aggregator import MetricsAggregator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/overview", summary="Aggregate platform statistics")
def metrics_overview(
    svc: AnalyticsService = Depends(get_analytics),
) -> Dict[str, Any]:
    """
    Return platform-wide aggregate statistics.

    Includes total requests, average latency, average risk score,
    hallucination rate, validation success rate, alert counts, high-risk
    case counts, and average pipeline execution time.
    """
    logger.debug("GET /metrics/overview")
    return svc.get_overview()


@router.get("/risk-trends", summary="Risk statistics by time period")
def metrics_risk_trends(
    aggregator: MetricsAggregator = Depends(get_metrics_aggregator),
) -> Dict[str, Any]:
    """
    Return hourly, daily, weekly, and monthly risk statistics.

    Each bucket includes count, avg/min/max risk scores, rolling averages,
    and trend indicators.
    """
    logger.debug("GET /metrics/risk-trends")
    return aggregator.aggregate_risk_trends()


@router.get("/hallucinations", summary="Hallucination analytics")
def metrics_hallucinations(
    aggregator: MetricsAggregator = Depends(get_metrics_aggregator),
) -> Dict[str, Any]:
    """
    Return hallucination detection rates broken down by time period
    (hourly, daily, weekly, monthly) with summary statistics and trend.
    """
    logger.debug("GET /metrics/hallucinations")
    return aggregator.aggregate_hallucinations()


@router.get("/validations", summary="Validation analytics")
def metrics_validations(
    aggregator: MetricsAggregator = Depends(get_metrics_aggregator),
) -> Dict[str, Any]:
    """
    Return validation success/failure rates broken down by time period
    with summary statistics and trend.
    """
    logger.debug("GET /metrics/validations")
    return aggregator.aggregate_validations()


@router.get("/performance", summary="Latency and execution metrics")
def metrics_performance(
    aggregator: MetricsAggregator = Depends(get_metrics_aggregator),
) -> Dict[str, Any]:
    """
    Return latency and pipeline execution time metrics broken down by
    time period with summary statistics and trend.
    """
    logger.debug("GET /metrics/performance")
    return aggregator.aggregate_performance()


@router.get("/agents", summary="Per-agent execution metrics")
def metrics_agents(
    svc: AgentMetricsService = Depends(get_agent_metrics),
) -> Dict[str, Any]:
    """
    Return per-agent statistics: execution count, success/failure rates,
    average/min/max latency, total execution time, and last execution
    timestamp for every agent seen by the platform.
    """
    logger.debug("GET /metrics/agents")
    return {"agents": svc.get_all()}
