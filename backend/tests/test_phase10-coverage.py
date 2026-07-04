"""
test_phase10_coverage.py
------------------------
Supplemental tests that push coverage of:
- backend/main.py
- backend/middleware/analytics_middleware.py
- backend/services/system_health_service.py (psutil / disk paths)
- backend/dependencies.py
- AgentMetrics dataclass derived properties
- MetricsAggregator edge cases
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ===========================================================================
# main.py — import and startup
# ===========================================================================


class TestMain:
    def test_app_importable_and_root_returns_200(self, tmp_path, monkeypatch):
        """Import main.py and verify the root endpoint works."""
        # Point storage to tmp_path so we don't pollute the real data dir
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "analytics").mkdir(parents=True)

        # Invalidate lru_cache so the monkeypatched cwd is used
        import backend.dependencies as deps

        deps.get_analytics.cache_clear()
        deps.get_agent_metrics.cache_clear()
        deps.get_metrics_aggregator.cache_clear()
        deps.get_health_service.cache_clear()
        deps.get_tracer.cache_clear()

        from backend.main import app

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["phase"] == 10


# ===========================================================================
# analytics_middleware.py
# ===========================================================================


class TestAnalyticsMiddleware:
    def _make_middleware_app(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        from backend.middleware.analytics_middleware import AnalyticsMiddleware
        from backend.services.analytics_service import AnalyticsService

        analytics = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
        )

        app = FastAPI()
        app.add_middleware(
            AnalyticsMiddleware,
            analytics_service=analytics,
            tracked_paths=("/analyze",),
        )

        @app.post("/analyze")
        def analyze():
            return JSONResponse(
                {
                    "risk_score": 0.75,
                    "hallucination_detected": True,
                    "validation_success": False,
                    "alerts_generated": 3,
                    "pipeline_execution_time_ms": 88.5,
                }
            )

        @app.get("/other")
        def other():
            return {"untracked": True}

        return app, analytics

    def test_tracked_path_records_snapshot(self, tmp_path):
        app, analytics = self._make_middleware_app(tmp_path)
        client = TestClient(app)
        client.post("/analyze")
        assert analytics.get_overview()["total_requests"] == 1

    def test_untracked_path_ignored(self, tmp_path):
        app, analytics = self._make_middleware_app(tmp_path)
        client = TestClient(app)
        client.get("/other")
        assert analytics.get_overview()["total_requests"] == 0

    def test_analytics_fields_extracted_correctly(self, tmp_path):
        app, analytics = self._make_middleware_app(tmp_path)
        client = TestClient(app)
        client.post("/analyze")
        ov = analytics.get_overview()
        assert ov["high_risk_cases"] == 1        # risk >= 0.7
        assert ov["hallucination_rate"] == 1.0
        # validation_success=False in response → rate=0.0
        assert ov["validation_success_rate"] == 0.0
        assert ov["alerts_generated"] == 3

    def test_nested_risk_field_extraction(self, tmp_path):
        """Test fallback field extraction for nested response shapes."""
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        from backend.middleware.analytics_middleware import AnalyticsMiddleware
        from backend.services.analytics_service import AnalyticsService

        analytics = AnalyticsService(
            storage_path=tmp_path / "s2.json",
            history_path=tmp_path / "h2.json",
        )
        app = FastAPI()
        app.add_middleware(
            AnalyticsMiddleware,
            analytics_service=analytics,
            tracked_paths=("/analyze",),
        )

        @app.post("/analyze")
        def analyze():
            return JSONResponse(
                {
                    "risk": {"score": 0.9},
                    "hallucinations": {"detected": True},
                    "validation": {"passed": True},
                    "alerts": ["a1", "a2"],
                }
            )

        client = TestClient(app)
        client.post("/analyze")
        ov = analytics.get_overview()
        assert ov["total_requests"] == 1
        assert ov["high_risk_cases"] == 1

    def test_non_200_response_not_recorded(self, tmp_path):
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        from backend.middleware.analytics_middleware import AnalyticsMiddleware
        from backend.services.analytics_service import AnalyticsService

        analytics = AnalyticsService(
            storage_path=tmp_path / "s3.json",
            history_path=tmp_path / "h3.json",
        )
        app = FastAPI()
        app.add_middleware(
            AnalyticsMiddleware,
            analytics_service=analytics,
            tracked_paths=("/analyze",),
        )

        @app.post("/analyze")
        def analyze():
            return JSONResponse({"error": "bad request"}, status_code=400)

        client = TestClient(app)
        client.post("/analyze")
        assert analytics.get_overview()["total_requests"] == 0


# ===========================================================================
# system_health_service.py — psutil / disk path coverage
# ===========================================================================


class TestSystemHealthServiceCoverage:
    def test_check_system_with_mocked_psutil(self, tmp_path):
        """Test the psutil-present code path."""
        from backend.services.system_health_service import SystemHealthService
        import psutil

        svc = SystemHealthService(data_dir=tmp_path)
        result = svc.check_system()
        # As long as it returns a component it's exercising the psutil path
        assert result.component == "system"
        assert "python_version" in result.details

    def test_check_system_psutil_not_installed(self, tmp_path):
        """Simulate psutil ImportError graceful degradation."""
        import sys
        import importlib

        from backend.services.system_health_service import SystemHealthService

        svc = SystemHealthService(data_dir=tmp_path)
        with patch("backend.services.system_health_service.psutil") as mock_psutil:
            mock_psutil.virtual_memory.side_effect = ImportError("no psutil")
            result = svc.check_system()
        assert result.component == "system"

    def test_storage_check_with_analytics_and_agent(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService
        from backend.services.agent_metrics_service import AgentMetricsService
        from backend.services.system_health_service import SystemHealthService

        analytics = AnalyticsService(
            storage_path=tmp_path / "s.json",
            history_path=tmp_path / "h.json",
        )
        agents = AgentMetricsService(storage_path=tmp_path / "a.json")
        svc = SystemHealthService(
            analytics_service=analytics,
            agent_metrics_service=agents,
            data_dir=tmp_path,
        )
        result = svc.check_storage()
        assert "analytics_storage_writable" in result.details
        assert "agent_metrics_path" in result.details

    def test_check_system_high_memory_triggers_recommendation(self, tmp_path):
        from backend.services.system_health_service import SystemHealthService

        svc = SystemHealthService(data_dir=tmp_path)

        class _Mem:
            total = 8 * 1024 ** 3
            available = 800 * 1024 ** 2
            percent = 80.0  # above 75, below 90

        class _Disk:
            free = 50 * 1024 ** 3
            percent = 30.0

        with patch("backend.services.system_health_service.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value = _Mem()
            mock_psutil.cpu_percent.return_value = 10.0
            mock_psutil.disk_usage.return_value = _Disk()
            result = svc.check_system()

        assert any("elevated" in r or "monitor" in r for r in result.recommendations)

    def test_check_system_critical_memory_is_unhealthy(self, tmp_path):
        from backend.services.system_health_service import SystemHealthService

        svc = SystemHealthService(data_dir=tmp_path)

        class _Mem:
            total = 8 * 1024 ** 3
            available = 200 * 1024 ** 2
            percent = 95.0

        class _Disk:
            free = 100 * 1024 ** 3
            percent = 20.0

        with patch("backend.services.system_health_service.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value = _Mem()
            mock_psutil.cpu_percent.return_value = 10.0
            mock_psutil.disk_usage.return_value = _Disk()
            result = svc.check_system()

        assert result.errors  # memory critical should produce an error

    def test_check_system_critical_disk_is_unhealthy(self, tmp_path):
        from backend.services.system_health_service import SystemHealthService

        svc = SystemHealthService(data_dir=tmp_path)

        class _Mem:
            total = 8 * 1024 ** 3
            available = 4 * 1024 ** 3
            percent = 50.0

        class _Disk:
            free = 500 * 1024 ** 2
            percent = 95.0

        with patch("backend.services.system_health_service.psutil") as mock_psutil:
            mock_psutil.virtual_memory.return_value = _Mem()
            mock_psutil.cpu_percent.return_value = 10.0
            mock_psutil.disk_usage.return_value = _Disk()
            result = svc.check_system()

        assert result.errors


# ===========================================================================
# dependencies.py — singleton behaviour
# ===========================================================================


class TestDependencies:
    def test_get_analytics_returns_same_instance(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "analytics").mkdir(parents=True)
        import backend.dependencies as deps

        deps.get_analytics.cache_clear()
        a1 = deps.get_analytics()
        a2 = deps.get_analytics()
        assert a1 is a2

    def test_get_tracer_returns_tracer(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "analytics").mkdir(parents=True)
        import backend.dependencies as deps
        from backend.middleware.observability import Tracer

        deps.get_tracer.cache_clear()
        tracer = deps.get_tracer()
        assert isinstance(tracer, Tracer)

    def test_get_metrics_aggregator_returns_aggregator(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data" / "analytics").mkdir(parents=True)
        import backend.dependencies as deps
        from backend.services.metrics_aggregator import MetricsAggregator

        deps.get_analytics.cache_clear()
        deps.get_metrics_aggregator.cache_clear()
        agg = deps.get_metrics_aggregator()
        assert isinstance(agg, MetricsAggregator)


# ===========================================================================
# AgentMetrics dataclass derived properties
# ===========================================================================


class TestAgentMetricsDataclass:
    def test_zero_execution_returns_zero_rates(self):
        from backend.services.agent_metrics_service import AgentMetrics

        m = AgentMetrics(agent_name="Empty")
        assert m.success_rate == 0.0
        assert m.failure_rate == 0.0
        assert m.average_latency_ms == 0.0

    def test_to_dict_includes_computed_properties(self):
        from backend.services.agent_metrics_service import AgentMetrics

        m = AgentMetrics(
            agent_name="A",
            execution_count=4,
            success_count=3,
            failure_count=1,
            total_execution_time_ms=400.0,
            minimum_latency_ms=80.0,
            maximum_latency_ms=120.0,
        )
        d = m.to_dict()
        assert d["success_rate"] == pytest.approx(0.75, abs=1e-4)
        assert d["failure_rate"] == pytest.approx(0.25, abs=1e-4)
        assert d["average_latency_ms"] == pytest.approx(100.0, abs=1e-3)


# ===========================================================================
# MetricsAggregator edge cases
# ===========================================================================


class TestMetricsAggregatorEdgeCases:
    def test_single_bucket_trend_is_stable(self, tmp_path):
        from backend.services.analytics_service import AnalyticsService
        from backend.services.metrics_aggregator import MetricsAggregator, _trend

        # Only one bucket → not enough data for a direction
        from backend.services.analytics_service import AnalyticsSnapshot
        from collections import defaultdict

        buckets = {"2024-01-01": [
            AnalyticsSnapshot(
                timestamp="2024-01-01T12:00:00+00:00",
                latency_ms=100.0,
                risk_score=0.5,
                hallucination_detected=False,
                validation_success=True,
                alerts_generated=0,
                high_risk=False,
                pipeline_execution_time_ms=90.0,
            )
        ]}
        result = _trend(buckets, "avg_risk_score")
        assert result == "stable"

    def test_rising_trend_detected(self):
        from backend.services.analytics_service import AnalyticsSnapshot
        from backend.services.metrics_aggregator import _trend

        def _snap(risk, day):
            return AnalyticsSnapshot(
                timestamp=f"2024-01-0{day}T12:00:00+00:00",
                latency_ms=100.0,
                risk_score=risk,
                hallucination_detected=False,
                validation_success=True,
                alerts_generated=0,
                high_risk=False,
                pipeline_execution_time_ms=90.0,
            )

        buckets = {
            "2024-01-01": [_snap(0.2, 1)],
            "2024-01-02": [_snap(0.8, 2)],
        }
        assert _trend(buckets) == "rising"

    def test_falling_trend_detected(self):
        from backend.services.analytics_service import AnalyticsSnapshot
        from backend.services.metrics_aggregator import _trend

        def _snap(risk, day):
            return AnalyticsSnapshot(
                timestamp=f"2024-01-0{day}T12:00:00+00:00",
                latency_ms=100.0,
                risk_score=risk,
                hallucination_detected=False,
                validation_success=True,
                alerts_generated=0,
                high_risk=False,
                pipeline_execution_time_ms=90.0,
            )

        buckets = {
            "2024-01-01": [_snap(0.8, 1)],
            "2024-01-02": [_snap(0.1, 2)],
        }
        assert _trend(buckets) == "falling"
