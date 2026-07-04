"""
test_phase10.py
---------------
Unit tests for Phase 10 services:
  - AnalyticsService
  - MetricsAggregator
  - AgentMetricsService
  - SystemHealthService
  - Observability / Tracer
  - Persistence & Retention

Coverage target: >90%
"""

from __future__ import annotations

import json
import logging
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snapshot(
    risk: float = 0.4,
    latency: float = 120.0,
    hallucination: bool = False,
    validation: bool = True,
    alerts: int = 0,
    high_risk: bool = False,
    pipeline_time: float = 100.0,
    ts: str | None = None,
    cid: str = "test-cid",
):
    from backend.services.analytics_service import AnalyticsSnapshot

    return AnalyticsSnapshot(
        timestamp=ts or datetime.now(timezone.utc).isoformat(),
        latency_ms=latency,
        risk_score=risk,
        hallucination_detected=hallucination,
        validation_success=validation,
        alerts_generated=alerts,
        high_risk=high_risk,
        pipeline_execution_time_ms=pipeline_time,
        correlation_id=cid,
    )


# ===========================================================================
# AnalyticsService
# ===========================================================================


class TestAnalyticsService:
    def _svc(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService

        return AnalyticsService(
            storage_path=tmp_path / "stats.json",
            history_path=tmp_path / "history.json",
            retention_days=30,
        )

    def test_initial_state_is_zero(self, tmp_path):
        svc = self._svc(tmp_path)
        ov = svc.get_overview()
        assert ov["total_requests"] == 0
        assert ov["average_latency_ms"] == 0.0

    def test_record_updates_totals(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record(_snapshot(risk=0.5, latency=200.0, alerts=2, high_risk=True))
        ov = svc.get_overview()
        assert ov["total_requests"] == 1
        assert ov["average_latency_ms"] == 200.0
        assert ov["average_risk_score"] == 0.5
        assert ov["alerts_generated"] == 2
        assert ov["high_risk_cases"] == 1

    def test_hallucination_rate(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record(_snapshot(hallucination=True))
        svc.record(_snapshot(hallucination=False))
        ov = svc.get_overview()
        assert ov["hallucination_rate"] == 0.5

    def test_validation_success_rate(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record(_snapshot(validation=True))
        svc.record(_snapshot(validation=False))
        ov = svc.get_overview()
        assert ov["validation_success_rate"] == 0.5

    def test_persistence_round_trip(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record(_snapshot(risk=0.9, alerts=3))
        # Reload from disk
        from backend.services.analytics_service import AnalyticsService

        svc2 = AnalyticsService(
            storage_path=tmp_path / "stats.json",
            history_path=tmp_path / "history.json",
        )
        ov = svc2.get_overview()
        assert ov["total_requests"] == 1
        assert ov["alerts_generated"] == 3

    def test_history_filtering(self, tmp_path):
        svc = self._svc(tmp_path)
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        svc.record(_snapshot(ts=old_ts))
        svc.record(_snapshot())  # now

        since = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent = svc.get_history(since=since)
        assert len(recent) == 1

    def test_retention_policy_prunes_old_records(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService

        svc = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
            retention_days=1,
        )
        old_ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        # Bypass record() to inject old snapshot
        svc._history.append(_snapshot(ts=old_ts))
        svc._prune_history()
        assert len(svc._history) == 0

    def test_reset_clears_everything(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record(_snapshot())
        svc.reset()
        ov = svc.get_overview()
        assert ov["total_requests"] == 0
        assert svc.get_history() == []

    def test_thread_safety(self, tmp_path):
        svc = self._svc(tmp_path)
        errors = []

        def worker():
            try:
                for _ in range(20):
                    svc.record(_snapshot())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert svc.get_overview()["total_requests"] == 100

    def test_corrupted_storage_recovers_gracefully(self, tmp_path):
        storage = tmp_path / "stats.json"
        history = tmp_path / "history.json"
        storage.write_text("NOT JSON {{{")
        history.write_text("NOT JSON [[[")
        from backend.services.analytics_service import AnalyticsService

        svc = AnalyticsService(storage_path=storage, history_path=history)
        # Should not raise; should start fresh
        assert svc.get_overview()["total_requests"] == 0

    def test_storage_healthy(self, tmp_path):
        svc = self._svc(tmp_path)
        assert svc.storage_healthy() is True

    def test_get_stats_returns_copy(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record(_snapshot())
        stats = svc.get_stats()
        stats.total_requests = 999
        assert svc.get_overview()["total_requests"] == 1  # original unchanged


# ===========================================================================
# MetricsAggregator
# ===========================================================================


class TestMetricsAggregator:
    def _setup(self, tmp_path, snapshots):
        from backend.services.analytics_service import AnalyticsService
        from backend.services.metrics_aggregator import MetricsAggregator

        svc = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
        )
        for snap in snapshots:
            svc.record(snap)
        return MetricsAggregator(svc)

    def test_risk_trends_returns_all_periods(self, tmp_path):
        agg = self._setup(tmp_path, [_snapshot(), _snapshot(risk=0.6)])
        result = agg.aggregate_risk_trends()
        assert "hourly" in result
        assert "daily" in result
        assert "weekly" in result
        assert "monthly" in result

    def test_daily_bucket_stats(self, tmp_path):
        snaps = [_snapshot(risk=0.2), _snapshot(risk=0.8)]
        agg = self._setup(tmp_path, snaps)
        result = agg.aggregate_risk_trends()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in result["daily"]
        bucket = result["daily"][today]
        assert bucket["count"] == 2
        assert bucket["min_risk_score"] == pytest.approx(0.2, abs=1e-4)
        assert bucket["max_risk_score"] == pytest.approx(0.8, abs=1e-4)

    def test_empty_history_returns_empty_dicts(self, tmp_path):
        agg = self._setup(tmp_path, [])
        result = agg.aggregate_risk_trends()
        assert result["hourly"] == {}
        assert result["daily"] == {}

    def test_hallucination_aggregation(self, tmp_path):
        snaps = [_snapshot(hallucination=True), _snapshot(hallucination=False)]
        agg = self._setup(tmp_path, snaps)
        result = agg.aggregate_hallucinations()
        assert "summary" in result
        assert result["summary"]["hallucination_rate"] == pytest.approx(0.5, abs=1e-4)

    def test_validation_aggregation(self, tmp_path):
        snaps = [_snapshot(validation=True), _snapshot(validation=False)]
        agg = self._setup(tmp_path, snaps)
        result = agg.aggregate_validations()
        assert result["summary"]["validation_success_rate"] == pytest.approx(0.5, abs=1e-4)

    def test_performance_aggregation(self, tmp_path):
        snaps = [_snapshot(latency=100.0), _snapshot(latency=200.0)]
        agg = self._setup(tmp_path, snaps)
        result = agg.aggregate_performance()
        assert result["summary"]["avg_latency_ms"] == pytest.approx(150.0, abs=1e-3)

    def test_rolling_average_present(self, tmp_path):
        snaps = [_snapshot() for _ in range(5)]
        agg = self._setup(tmp_path, snaps)
        result = agg.aggregate_risk_trends()
        # rolling_avg_risk should be present in each daily bucket
        for bucket in result["daily"].values():
            assert "rolling_avg_risk" in bucket

    def test_trend_key_present_in_latest_bucket(self, tmp_path):
        snaps = [_snapshot(), _snapshot(risk=0.9)]
        agg = self._setup(tmp_path, snaps)
        result = agg.aggregate_risk_trends()
        daily = result["daily"]
        latest_key = sorted(daily.keys())[-1]
        assert "trend" in daily[latest_key]

    def test_summary_statistics_keys(self, tmp_path):
        agg = self._setup(tmp_path, [_snapshot(risk=0.3, alerts=1)])
        s = agg.summary_statistics()
        expected_keys = {
            "count", "avg_risk_score", "min_risk_score", "max_risk_score",
            "avg_latency_ms", "hallucination_rate", "validation_success_rate",
            "total_alerts", "high_risk_cases", "avg_pipeline_time_ms",
        }
        assert expected_keys.issubset(s.keys())


# ===========================================================================
# AgentMetricsService
# ===========================================================================


class TestAgentMetricsService:
    def _svc(self, tmp_path):
        from backend.services.agent_metrics_service import AgentMetricsService

        return AgentMetricsService(storage_path=tmp_path / "agents.json")

    def test_new_agent_auto_registered(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_execution("RiskAgent", 50.0, success=True)
        assert "RiskAgent" in svc.get_all()

    def test_success_increments(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_execution("A", 10.0, True)
        svc.record_execution("A", 20.0, True)
        m = svc.get_agent("A")
        assert m["execution_count"] == 2
        assert m["success_count"] == 2
        assert m["failure_count"] == 0
        assert m["success_rate"] == 1.0

    def test_failure_increments(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_execution("A", 10.0, True)
        svc.record_execution("A", 10.0, False)
        m = svc.get_agent("A")
        assert m["failure_rate"] == pytest.approx(0.5, abs=1e-4)

    def test_latency_tracking(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_execution("A", 100.0, True)
        svc.record_execution("A", 200.0, True)
        m = svc.get_agent("A")
        assert m["minimum_latency_ms"] == pytest.approx(100.0)
        assert m["maximum_latency_ms"] == pytest.approx(200.0)
        assert m["average_latency_ms"] == pytest.approx(150.0)

    def test_persistence_round_trip(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_execution("Agent1", 75.0, True)
        from backend.services.agent_metrics_service import AgentMetricsService

        svc2 = AgentMetricsService(storage_path=tmp_path / "agents.json")
        m = svc2.get_agent("Agent1")
        assert m is not None
        assert m["execution_count"] == 1

    def test_unknown_agent_returns_none(self, tmp_path):
        svc = self._svc(tmp_path)
        assert svc.get_agent("NonExistent") is None

    def test_multiple_agents_tracked_independently(self, tmp_path):
        svc = self._svc(tmp_path)
        for name in ["AgentA", "AgentB", "AgentC"]:
            svc.record_execution(name, 50.0, True)
        all_agents = svc.get_all()
        assert len(all_agents) == 3

    def test_timer_context_manager_success(self, tmp_path):
        svc = self._svc(tmp_path)
        with svc.timer("TimedAgent"):
            time.sleep(0.01)
        m = svc.get_agent("TimedAgent")
        assert m["execution_count"] == 1
        assert m["success_count"] == 1
        assert m["average_latency_ms"] >= 10.0

    def test_timer_context_manager_failure(self, tmp_path):
        svc = self._svc(tmp_path)
        with pytest.raises(ValueError):
            with svc.timer("FailingAgent"):
                raise ValueError("boom")
        m = svc.get_agent("FailingAgent")
        assert m["failure_count"] == 1

    def test_reset_clears_all(self, tmp_path):
        svc = self._svc(tmp_path)
        svc.record_execution("X", 1.0, True)
        svc.reset()
        assert svc.get_all() == {}

    def test_thread_safety(self, tmp_path):
        svc = self._svc(tmp_path)
        errors = []

        def worker(name):
            try:
                for _ in range(10):
                    svc.record_execution(name, 5.0, True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"Agent{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


# ===========================================================================
# SystemHealthService
# ===========================================================================


class TestSystemHealthService:
    def _svc(self, tmp_path, analytics_svc=None, agent_svc=None):
        from backend.services.system_health_service import SystemHealthService

        return SystemHealthService(
            analytics_service=analytics_svc,
            agent_metrics_service=agent_svc,
            data_dir=tmp_path,
        )

    def test_full_health_returns_all_components(self, tmp_path):
        svc = self._svc(tmp_path)
        report = svc.get_full_health()
        component_names = {c.component for c in report.components}
        assert {"pipeline", "storage", "models", "system"}.issubset(component_names)

    def test_full_health_to_dict_structure(self, tmp_path):
        svc = self._svc(tmp_path)
        d = svc.get_full_health().to_dict()
        assert "overall_status" in d
        assert "timestamp" in d
        assert "components" in d
        assert isinstance(d["components"], list)

    def test_storage_healthy_when_writable(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.check_storage()
        assert result.status.value in ("healthy", "degraded")

    def test_pipeline_healthy_with_analytics(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService

        analytics = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
        )
        svc = self._svc(tmp_path, analytics_svc=analytics)
        result = svc.check_pipeline()
        assert result.status.value == "healthy"
        assert result.details["total_requests"] == 0

    def test_pipeline_without_analytics_service(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.check_pipeline()
        assert result.component == "pipeline"

    def test_models_healthy_when_none_configured(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.check_models()
        assert result.status.value == "healthy"
        assert "note" in result.details

    def test_models_unhealthy_when_missing(self, tmp_path):
        from backend.services.system_health_service import SystemHealthService

        svc = SystemHealthService(
            data_dir=tmp_path,
            ml_model_paths=[tmp_path / "missing_model.pkl"],
        )
        result = svc.check_models()
        assert result.status.value == "unhealthy"
        assert result.errors

    def test_models_healthy_when_present(self, tmp_path):
        model_file = tmp_path / "model.pkl"
        model_file.write_bytes(b"fake model")
        from backend.services.system_health_service import SystemHealthService

        svc = SystemHealthService(
            data_dir=tmp_path,
            ml_model_paths=[model_file],
        )
        result = svc.check_models()
        assert result.status.value == "healthy"

    def test_system_check_returns_component_health(self, tmp_path):
        svc = self._svc(tmp_path)
        result = svc.check_system()
        assert result.component == "system"
        assert "timestamp" in result.to_dict()

    def test_component_health_to_dict(self, tmp_path):
        svc = self._svc(tmp_path)
        h = svc.check_pipeline()
        d = h.to_dict()
        for key in ("component", "status", "timestamp", "details", "errors", "recommendations"):
            assert key in d

    def test_aggregate_status_unhealthy_propagates(self, tmp_path):
        from backend.services.system_health_service import HealthStatus, SystemHealthService

        result = SystemHealthService._aggregate_status(
            [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
        )
        assert result == HealthStatus.UNHEALTHY

    def test_aggregate_status_degraded_propagates(self, tmp_path):
        from backend.services.system_health_service import HealthStatus, SystemHealthService

        result = SystemHealthService._aggregate_status(
            [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        )
        assert result == HealthStatus.DEGRADED


# ===========================================================================
# Observability / Tracer
# ===========================================================================


class TestObservability:
    def test_new_correlation_id_generates_uuid(self):
        from backend.middleware.observability import new_correlation_id

        cid = new_correlation_id()
        assert len(cid) == 36  # UUID4 format

    def test_set_and_get_correlation_id(self):
        from backend.middleware.observability import get_correlation_id, set_correlation_id

        set_correlation_id("my-custom-id")
        assert get_correlation_id() == "my-custom-id"

    def test_tracer_starts_and_finishes_trace(self):
        from backend.middleware.observability import Tracer, set_correlation_id

        set_correlation_id("trace-test")
        tracer = Tracer()
        trace = tracer.start_trace(env="test")
        assert trace.correlation_id == "trace-test"
        tracer.finish_trace(trace)
        assert trace.total_duration_ms is not None
        assert trace.total_duration_ms >= 0

    def test_tracer_span_records_timing(self):
        from backend.middleware.observability import Tracer, new_correlation_id

        new_correlation_id()
        tracer = Tracer()
        trace = tracer.start_trace()
        with tracer.span(trace, "TestAgent"):
            time.sleep(0.01)
        tracer.finish_trace(trace)
        assert len(trace.spans) == 1
        span = trace.spans[0]
        assert span.name == "TestAgent"
        assert span.duration_ms >= 10.0

    def test_tracer_span_records_error_on_exception(self):
        from backend.middleware.observability import Tracer, new_correlation_id

        new_correlation_id()
        tracer = Tracer()
        trace = tracer.start_trace()
        with pytest.raises(RuntimeError):
            with tracer.span(trace, "BrokenAgent"):
                raise RuntimeError("agent failed")
        span = trace.spans[0]
        assert span.error == "agent failed"

    def test_trace_to_dict(self):
        from backend.middleware.observability import Tracer, new_correlation_id

        new_correlation_id()
        tracer = Tracer()
        trace = tracer.start_trace()
        with tracer.span(trace, "Span1"):
            pass
        tracer.finish_trace(trace)
        d = trace.to_dict()
        assert "correlation_id" in d
        assert "total_duration_ms" in d
        assert len(d["spans"]) == 1

    def test_multiple_spans_tracked(self):
        from backend.middleware.observability import Tracer, new_correlation_id

        new_correlation_id()
        tracer = Tracer()
        trace = tracer.start_trace()
        for name in ["A", "B", "C"]:
            with tracer.span(trace, name):
                pass
        tracer.finish_trace(trace)
        assert len(trace.spans) == 3

    def test_correlation_log_formatter(self):
        from backend.middleware.observability import (
            CorrelationLogFormatter,
            set_correlation_id,
        )

        set_correlation_id("log-test-id")
        formatter = CorrelationLogFormatter(fmt="%(correlation_id)s %(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "log-test-id" in output

    def test_span_finish_sets_end_time(self):
        from backend.middleware.observability import Span

        s = Span(name="test")
        assert s.duration_ms is None
        s.finish()
        assert s.duration_ms is not None

    def test_span_to_dict(self):
        from backend.middleware.observability import Span

        s = Span(name="x", metadata={"key": "val"})
        s.finish()
        d = s.to_dict()
        assert d["name"] == "x"
        assert "duration_ms" in d


# ===========================================================================
# Analytics persistence & retention
# ===========================================================================


class TestPersistenceAndRetention:
    def test_stats_file_created_on_first_record(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService

        svc = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
        )
        svc.record(_snapshot())
        assert (tmp_path / "s.json").exists()
        assert (tmp_path / "h.json").exists()

    def test_history_file_valid_json(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService

        svc = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
        )
        svc.record(_snapshot())
        data = json.loads((tmp_path / "h.json").read_text())
        assert isinstance(data, list)
        assert data[0]["correlation_id"] == "test-cid"

    def test_retention_removes_records_older_than_cutoff(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService

        svc = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
            retention_days=7,
        )
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        recent = datetime.now(timezone.utc).isoformat()
        svc.record(_snapshot(ts=old))
        svc.record(_snapshot(ts=recent))
        # Reload to trigger pruning
        svc2 = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
            retention_days=7,
        )
        svc2._prune_history()
        assert len(svc2._history) == 1

    def test_stats_file_valid_json_after_record(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService

        svc = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
        )
        svc.record(_snapshot(risk=0.77))
        data = json.loads((tmp_path / "s.json").read_text())
        assert "total_requests" in data
        assert data["total_requests"] == 1


# ===========================================================================
# Backward compatibility placeholder
# ---------------------------------------------------------------------------
# These tests verify that importing Phase 9 modules (if present) still works
# and that Phase 10 does not break their public APIs.  Since Phase 9 code is
# not included in this repository stub, the tests simply confirm that Phase 10
# modules can be imported in isolation without side effects.
# ===========================================================================


class TestBackwardCompatibility:
    def test_analytics_service_importable(self):
        from backend.services import analytics_service  # noqa: F401

    def test_metrics_aggregator_importable(self):
        from backend.services import metrics_aggregator  # noqa: F401

    def test_agent_metrics_service_importable(self):
        from backend.services import agent_metrics_service  # noqa: F401

    def test_system_health_service_importable(self):
        from backend.services import system_health_service  # noqa: F401

    def test_observability_importable(self):
        from backend.middleware import observability  # noqa: F401

    def test_analytics_middleware_importable(self):
        from backend.middleware import analytics_middleware  # noqa: F401

    def test_metrics_router_importable(self):
        from backend.routers import metrics_router  # noqa: F401

    def test_health_router_importable(self):
        from backend.routers import health_router  # noqa: F401

    def test_dependencies_importable(self):
        from backend import dependencies  # noqa: F401
