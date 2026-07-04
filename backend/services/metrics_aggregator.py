"""
metrics_aggregator.py
---------------------
Aggregate AnalyticsSnapshots from AnalyticsService into time-bucketed
statistical summaries (hourly, daily, weekly, monthly).

All aggregation operates on persisted history rather than re-running
pipeline executions, so results remain consistent across restarts.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.analytics_service import AnalyticsService, AnalyticsSnapshot

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bucket helpers
# ---------------------------------------------------------------------------


def _bucket_hourly(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:00:00+00:00")


def _bucket_daily(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d")


def _bucket_weekly(ts: datetime) -> str:
    # ISO week: year-Www
    return ts.strftime("%G-W%V")


def _bucket_monthly(ts: datetime) -> str:
    return ts.strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Statistics builder
# ---------------------------------------------------------------------------


def _build_stats(snapshots: List[AnalyticsSnapshot]) -> Dict[str, Any]:
    """Compute summary statistics for a list of snapshots."""
    n = len(snapshots)
    if n == 0:
        return {
            "count": 0,
            "avg_risk_score": None,
            "min_risk_score": None,
            "max_risk_score": None,
            "avg_latency_ms": None,
            "min_latency_ms": None,
            "max_latency_ms": None,
            "hallucination_rate": None,
            "validation_success_rate": None,
            "total_alerts": 0,
            "high_risk_cases": 0,
            "avg_pipeline_time_ms": None,
        }

    risks = [s.risk_score for s in snapshots]
    latencies = [s.latency_ms for s in snapshots]
    pipeline_times = [s.pipeline_execution_time_ms for s in snapshots]
    hallucinations = sum(1 for s in snapshots if s.hallucination_detected)
    validations = sum(1 for s in snapshots if s.validation_success)
    alerts = sum(s.alerts_generated for s in snapshots)
    high_risk = sum(1 for s in snapshots if s.high_risk)

    return {
        "count": n,
        "avg_risk_score": round(statistics.mean(risks), 4),
        "min_risk_score": round(min(risks), 4),
        "max_risk_score": round(max(risks), 4),
        "avg_latency_ms": round(statistics.mean(latencies), 3),
        "min_latency_ms": round(min(latencies), 3),
        "max_latency_ms": round(max(latencies), 3),
        "hallucination_rate": round(hallucinations / n, 4),
        "validation_success_rate": round(validations / n, 4),
        "total_alerts": alerts,
        "high_risk_cases": high_risk,
        "avg_pipeline_time_ms": round(statistics.mean(pipeline_times), 3),
    }


def _rolling_average(
    buckets: Dict[str, List[AnalyticsSnapshot]],
    window: int,
    key_fn: str = "avg_risk_score",
) -> Dict[str, Optional[float]]:
    """
    Compute a rolling average of *key_fn* over *window* consecutive buckets.

    Returns a dict mapping bucket label → rolling average value.
    """
    sorted_keys = sorted(buckets.keys())
    stats_list = [_build_stats(buckets[k]) for k in sorted_keys]
    rolling: Dict[str, Optional[float]] = {}
    for i, k in enumerate(sorted_keys):
        window_vals = [
            stats_list[j][key_fn]
            for j in range(max(0, i - window + 1), i + 1)
            if stats_list[j][key_fn] is not None
        ]
        rolling[k] = round(statistics.mean(window_vals), 4) if window_vals else None
    return rolling


def _trend(buckets: Dict[str, List[AnalyticsSnapshot]], key_fn: str = "avg_risk_score") -> str:
    """Return 'rising', 'falling', or 'stable' based on last two non-None bucket values."""
    sorted_keys = sorted(buckets.keys())
    values = [
        _build_stats(buckets[k])[key_fn]
        for k in sorted_keys
        if _build_stats(buckets[k])[key_fn] is not None
    ]
    if len(values) < 2:
        return "stable"
    delta = values[-1] - values[-2]
    if abs(delta) < 0.005:
        return "stable"
    return "rising" if delta > 0 else "falling"


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


class MetricsAggregator:
    """
    Aggregates historical AnalyticsSnapshots from AnalyticsService into
    time-bucketed statistics.

    Parameters
    ----------
    analytics_service:
        Source of historical snapshots.
    rolling_window_size:
        Number of buckets used for rolling average computation.
    """

    def __init__(
        self,
        analytics_service: AnalyticsService,
        rolling_window_size: int = 7,
    ) -> None:
        self._svc = analytics_service
        self._window = rolling_window_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def aggregate_risk_trends(self) -> Dict[str, Any]:
        """Return hourly/daily/weekly/monthly risk statistics."""
        snapshots = self._svc.get_history()
        return {
            "hourly": self._aggregate(snapshots, _bucket_hourly),
            "daily": self._aggregate(snapshots, _bucket_daily),
            "weekly": self._aggregate(snapshots, _bucket_weekly),
            "monthly": self._aggregate(snapshots, _bucket_monthly),
        }

    def aggregate_hallucinations(self) -> Dict[str, Any]:
        """Return hallucination breakdown by time period."""
        snapshots = self._svc.get_history()
        return self._build_period_breakdown(snapshots, "hallucination_rate")

    def aggregate_validations(self) -> Dict[str, Any]:
        """Return validation breakdown by time period."""
        snapshots = self._svc.get_history()
        return self._build_period_breakdown(snapshots, "validation_success_rate")

    def aggregate_performance(self) -> Dict[str, Any]:
        """Return latency/execution-time breakdown by time period."""
        snapshots = self._svc.get_history()
        return self._build_period_breakdown(snapshots, "avg_latency_ms")

    def summary_statistics(self) -> Dict[str, Any]:
        """Return overall summary statistics across all history."""
        snapshots = self._svc.get_history()
        return _build_stats(snapshots)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bucket_snapshots(
        self, snapshots: List[AnalyticsSnapshot], bucket_fn
    ) -> Dict[str, List[AnalyticsSnapshot]]:
        buckets: Dict[str, List[AnalyticsSnapshot]] = defaultdict(list)
        for s in snapshots:
            try:
                ts = datetime.fromisoformat(s.timestamp).replace(tzinfo=timezone.utc)
                buckets[bucket_fn(ts)].append(s)
            except Exception as exc:
                logger.debug("Skipping snapshot with bad timestamp: %s", exc)
        return dict(buckets)

    def _aggregate(
        self,
        snapshots: List[AnalyticsSnapshot],
        bucket_fn,
    ) -> Dict[str, Any]:
        buckets = self._bucket_snapshots(snapshots, bucket_fn)
        result: Dict[str, Any] = {}
        for label in sorted(buckets.keys()):
            result[label] = _build_stats(buckets[label])
        rolling = _rolling_average(buckets, self._window)
        for label in result:
            result[label]["rolling_avg_risk"] = rolling.get(label)
        # append trend to the most recent bucket
        if result:
            latest = sorted(result.keys())[-1]
            result[latest]["trend"] = _trend(buckets)
        return result

    def _build_period_breakdown(
        self, snapshots: List[AnalyticsSnapshot], primary_key: str
    ) -> Dict[str, Any]:
        return {
            "hourly": self._aggregate(snapshots, _bucket_hourly),
            "daily": self._aggregate(snapshots, _bucket_daily),
            "weekly": self._aggregate(snapshots, _bucket_weekly),
            "monthly": self._aggregate(snapshots, _bucket_monthly),
            "summary": _build_stats(snapshots),
            "trend": _trend(
                self._bucket_snapshots(snapshots, _bucket_daily),
                primary_key,
            ),
        }
