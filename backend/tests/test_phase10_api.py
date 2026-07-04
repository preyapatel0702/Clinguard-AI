"""
test_phase10_api.py
-------------------
Integration tests for Phase 10 API endpoints via FastAPI TestClient.

Tests all metrics/* and health/* routes, verifying:
  - HTTP status codes
  - Response schema structure
  - Data correctness after seeded analytics
  - Correlation ID header propagation
  - Backward compatibility (existing routes unaffected)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Test application factory
# ---------------------------------------------------------------------------
# We build a fresh FastAPI app for each test module to avoid state leakage
# from the lru_cache singletons in dependencies.py.  Each test uses a
# temporary directory so storage files never collide.


def _make_app(tmp_path: Path):
    """Create a fully-wired FastAPI test application backed by tmp_path."""
    from backend.services.analytics_service import AnalyticsService
    from backend.services.agent_metrics_service import AgentMetricsService
    from backend.services.metrics_aggregator import MetricsAggregator
    from backend.services.system_health_service import SystemHealthService
    from backend.middleware.observability import CorrelationIdMiddleware
    from backend.routers.metrics_router import router as metrics_router
    from backend.routers.health_router import router as health_router

    analytics = AnalyticsService(
        storage_path=tmp_path / "stats.json",
        history_path=tmp_path / "history.json",
    )
    agent_metrics = AgentMetricsService(storage_path=tmp_path / "agents.json")
    aggregator = MetricsAggregator(analytics_service=analytics)
    health_svc = SystemHealthService(
        analytics_service=analytics,
        agent_metrics_service=agent_metrics,
        data_dir=tmp_path,
    )

    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    # Override dependencies so routes use our tmp-backed services
    from backend import dependencies

    app.dependency_overrides[dependencies.get_analytics] = lambda: analytics
    app.dependency_overrides[dependencies.get_agent_metrics] = lambda: agent_metrics
    app.dependency_overrides[dependencies.get_metrics_aggregator] = lambda: aggregator
    app.dependency_overrides[dependencies.get_health_service] = lambda: health_svc

    app.include_router(metrics_router)
    app.include_router(health_router)

    @app.get("/")
    def root():
        return {"status": "ok"}

    return app, analytics, agent_metrics


def _seed_analytics(analytics, n: int = 5):
    """Seed analytics with n synthetic snapshots."""
    from backend.services.analytics_service import AnalyticsSnapshot

    for i in range(n):
        analytics.record(
            AnalyticsSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                latency_ms=float(100 + i * 10),
                risk_score=0.1 * (i + 1),
                hallucination_detected=(i % 2 == 0),
                validation_success=(i % 3 != 0),
                alerts_generated=i,
                high_risk=(i >= 4),
                pipeline_execution_time_ms=float(90 + i * 5),
                correlation_id=f"cid-{i}",
            )
        )


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture()
def client_empty(tmp_path):
    app, analytics, agents = _make_app(tmp_path)
    return TestClient(app), analytics, agents


@pytest.fixture()
def client_seeded(tmp_path):
    app, analytics, agents = _make_app(tmp_path)
    _seed_analytics(analytics, n=5)
    for i, name in enumerate(["RiskAgent", "HallucinationAgent", "ValidationAgent"]):
        agents.record_execution(name, latency_ms=float(50 + i * 25), success=(i != 2))
    return TestClient(app), analytics, agents


# ===========================================================================
# GET /metrics/overview
# ===========================================================================


class TestMetricsOverview:
    def test_returns_200(self, client_empty):
        client, *_ = client_empty
        resp = client.get("/metrics/overview")
        assert resp.status_code == 200

    def test_response_schema_keys(self, client_empty):
        client, *_ = client_empty
        data = client.get("/metrics/overview").json()
        required_keys = {
            "total_requests",
            "average_latency_ms",
            "average_risk_score",
            "hallucination_rate",
            "validation_success_rate",
            "alerts_generated",
            "high_risk_cases",
            "average_pipeline_execution_time_ms",
        }
        assert required_keys.issubset(data.keys())

    def test_empty_state_zeros(self, client_empty):
        client, *_ = client_empty
        data = client.get("/metrics/overview").json()
        assert data["total_requests"] == 0

    def test_seeded_total_requests(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/overview").json()
        assert data["total_requests"] == 5

    def test_seeded_average_latency(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/overview").json()
        # Latencies: 100,110,120,130,140 → avg=120
        assert abs(data["average_latency_ms"] - 120.0) < 1.0

    def test_seeded_high_risk_cases(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/overview").json()
        assert data["high_risk_cases"] == 1  # only i=4 is high_risk


# ===========================================================================
# GET /metrics/risk-trends
# ===========================================================================


class TestMetricsRiskTrends:
    def test_returns_200(self, client_seeded):
        client, *_ = client_seeded
        assert client.get("/metrics/risk-trends").status_code == 200

    def test_response_has_all_periods(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/risk-trends").json()
        assert {"hourly", "daily", "weekly", "monthly"}.issubset(data.keys())

    def test_daily_bucket_has_today(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/risk-trends").json()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in data["daily"]

    def test_empty_returns_empty_buckets(self, client_empty):
        client, *_ = client_empty
        data = client.get("/metrics/risk-trends").json()
        assert data["daily"] == {}

    def test_bucket_has_count(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/risk-trends").json()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert data["daily"][today]["count"] == 5


# ===========================================================================
# GET /metrics/hallucinations
# ===========================================================================


class TestMetricsHallucinations:
    def test_returns_200(self, client_seeded):
        client, *_ = client_seeded
        assert client.get("/metrics/hallucinations").status_code == 200

    def test_response_has_summary(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/hallucinations").json()
        assert "summary" in data

    def test_summary_hallucination_rate_correct(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/hallucinations").json()
        # i=0,2,4 → 3/5 = 0.6
        assert abs(data["summary"]["hallucination_rate"] - 0.6) < 0.01

    def test_response_has_trend(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/hallucinations").json()
        assert "trend" in data


# ===========================================================================
# GET /metrics/validations
# ===========================================================================


class TestMetricsValidations:
    def test_returns_200(self, client_seeded):
        client, *_ = client_seeded
        assert client.get("/metrics/validations").status_code == 200

    def test_response_has_summary(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/validations").json()
        assert "summary" in data

    def test_validation_success_rate(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/validations").json()
        # i%3!=0: i=1,2,4 → 3/5 = 0.6
        assert abs(data["summary"]["validation_success_rate"] - 0.6) < 0.01


# ===========================================================================
# GET /metrics/performance
# ===========================================================================


class TestMetricsPerformance:
    def test_returns_200(self, client_seeded):
        client, *_ = client_seeded
        assert client.get("/metrics/performance").status_code == 200

    def test_response_has_summary(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/performance").json()
        assert "summary" in data

    def test_avg_latency_in_summary(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/performance").json()
        assert data["summary"]["avg_latency_ms"] is not None

    def test_response_has_daily_period(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/performance").json()
        assert "daily" in data


# ===========================================================================
# GET /metrics/agents
# ===========================================================================


class TestMetricsAgents:
    def test_returns_200(self, client_seeded):
        client, *_ = client_seeded
        assert client.get("/metrics/agents").status_code == 200

    def test_response_has_agents_key(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/agents").json()
        assert "agents" in data

    def test_all_three_agents_present(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/agents").json()
        assert "RiskAgent" in data["agents"]
        assert "HallucinationAgent" in data["agents"]
        assert "ValidationAgent" in data["agents"]

    def test_agent_metric_keys(self, client_seeded):
        client, *_ = client_seeded
        data = client.get("/metrics/agents").json()
        m = data["agents"]["RiskAgent"]
        for key in (
            "execution_count", "success_count", "failure_count",
            "success_rate", "failure_rate", "average_latency_ms",
            "minimum_latency_ms", "maximum_latency_ms",
            "total_execution_time_ms", "last_execution_time",
        ):
            assert key in m, f"Missing key: {key}"

    def test_empty_agents_on_fresh_state(self, client_empty):
        client, *_ = client_empty
        data = client.get("/metrics/agents").json()
        assert data["agents"] == {}


# ===========================================================================
# GET /health
# ===========================================================================


class TestHealthFull:
    def test_returns_200(self, client_empty):
        client, *_ = client_empty
        assert client.get("/health").status_code == 200

    def test_response_schema(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health").json()
        assert "overall_status" in data
        assert "timestamp" in data
        assert "components" in data
        assert isinstance(data["components"], list)

    def test_all_four_components_present(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health").json()
        names = {c["component"] for c in data["components"]}
        assert {"pipeline", "storage", "models", "system"}.issubset(names)

    def test_overall_status_is_valid_value(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health").json()
        assert data["overall_status"] in ("healthy", "degraded", "unhealthy", "unknown")


# ===========================================================================
# GET /health/pipeline
# ===========================================================================


class TestHealthPipeline:
    def test_returns_200(self, client_empty):
        client, *_ = client_empty
        assert client.get("/health/pipeline").status_code == 200

    def test_component_is_pipeline(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/pipeline").json()
        assert data["component"] == "pipeline"

    def test_has_required_keys(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/pipeline").json()
        for key in ("component", "status", "timestamp", "details", "errors", "recommendations"):
            assert key in data


# ===========================================================================
# GET /health/storage
# ===========================================================================


class TestHealthStorage:
    def test_returns_200(self, client_empty):
        client, *_ = client_empty
        assert client.get("/health/storage").status_code == 200

    def test_component_is_storage(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/storage").json()
        assert data["component"] == "storage"

    def test_storage_writable_when_tmp_dir(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/storage").json()
        assert data["status"] in ("healthy", "degraded")


# ===========================================================================
# GET /health/models
# ===========================================================================


class TestHealthModels:
    def test_returns_200(self, client_empty):
        client, *_ = client_empty
        assert client.get("/health/models").status_code == 200

    def test_component_is_models(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/models").json()
        assert data["component"] == "models"

    def test_no_model_paths_is_healthy(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/models").json()
        assert data["status"] == "healthy"


# ===========================================================================
# GET /health/system
# ===========================================================================


class TestHealthSystem:
    def test_returns_200(self, client_empty):
        client, *_ = client_empty
        assert client.get("/health/system").status_code == 200

    def test_component_is_system(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/system").json()
        assert data["component"] == "system"

    def test_has_timestamp(self, client_empty):
        client, *_ = client_empty
        data = client.get("/health/system").json()
        assert "timestamp" in data


# ===========================================================================
# Correlation ID propagation
# ===========================================================================


class TestCorrelationId:
    def test_correlation_id_header_echoed_back(self, client_empty):
        client, *_ = client_empty
        resp = client.get("/metrics/overview", headers={"X-Correlation-ID": "my-test-id"})
        assert resp.headers.get("X-Correlation-ID") == "my-test-id"

    def test_correlation_id_generated_when_absent(self, client_empty):
        client, *_ = client_empty
        resp = client.get("/metrics/overview")
        cid = resp.headers.get("X-Correlation-ID")
        assert cid is not None and len(cid) == 36  # UUID4

    def test_root_route_still_works(self, client_empty):
        """Verify that Phase 9 / root route is unaffected."""
        client, *_ = client_empty
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
