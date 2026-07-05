"""
analytics_middleware.py
-----------------------
FastAPI / Starlette middleware that automatically collects analytics after
every completed ClinGuard-AI pipeline request.

No manual instrumentation needed in route handlers.  The middleware wraps
every request, measures wall-clock latency, extracts risk/hallucination/
validation fields from the response body, and records an AnalyticsSnapshot.

Works in tandem with the CorrelationIdMiddleware (which must be added first).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable

from backend.middleware.observability import get_correlation_id
from backend.services.analytics_service import AnalyticsService, AnalyticsSnapshot

logger = logging.getLogger(__name__)

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    _STARLETTE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _STARLETTE_AVAILABLE = False


def _as_dict(value: Any) -> dict:
    """Return *value* if it's a dict, else an empty dict (never raises)."""
    return value if isinstance(value, dict) else {}


def _extract_hallucination_detected(payload: dict) -> bool:
    """
    Determine whether any hallucination was detected in the response.

    Supports both the real ``AnalyzeResponse`` shape (``hallucinations`` is a
    list of ``HallucinationResult`` objects with an ``is_hallucination``
    flag) and legacy/simplified shapes (a flat ``hallucination_detected``
    bool, or a nested ``{"hallucinations": {"detected": bool}}`` dict).
    """
    if "hallucination_detected" in payload:
        return bool(payload.get("hallucination_detected"))

    hallucinations = payload.get("hallucinations")
    if isinstance(hallucinations, dict):
        return bool(hallucinations.get("detected", False))
    if isinstance(hallucinations, list):
        return any(
            bool(item.get("is_hallucination") or item.get("detected"))
            for item in hallucinations
            if isinstance(item, dict)
        )
    return False


def _extract_validation_success(payload: dict) -> bool:
    """
    Determine whether the response passed validation.

    Supports the real ``AnalyzeResponse`` shape (``validated_claims`` is a
    list of ``ValidationResult`` objects with an ``is_valid`` flag) and
    legacy/simplified shapes (a flat ``validation_success`` bool, or a
    nested ``{"validation": {"passed": bool}}`` dict). A response with no
    claims to validate is treated as a successful validation.
    """
    if "validation_success" in payload:
        return bool(payload.get("validation_success"))

    validation = payload.get("validation")
    if isinstance(validation, dict):
        return bool(validation.get("passed", True))

    claims = payload.get("validated_claims")
    if isinstance(claims, list):
        if not claims:
            return True
        return all(
            bool(claim.get("is_valid", True))
            for claim in claims
            if isinstance(claim, dict)
        )
    return True


def _extract_alerts_generated(payload: dict) -> int:
    """Count alerts generated, supporting both a count field and a list."""
    if "alerts_generated" in payload:
        return int(payload.get("alerts_generated") or 0)
    alerts = payload.get("alerts")
    if isinstance(alerts, list):
        return len(alerts)
    return 0


def _extract_high_risk(payload: dict, risk_score: Any) -> bool:
    """
    Determine whether the case should be classified as high risk.

    Supports a flat ``high_risk`` bool, the real ``risk_level`` string
    (HIGH/CRITICAL), or falls back to a risk-score threshold.
    """
    if "high_risk" in payload:
        return bool(payload.get("high_risk"))

    risk_level = payload.get("risk_level")
    if isinstance(risk_level, str) and risk_level.upper() in ("HIGH", "CRITICAL"):
        return True

    return isinstance(risk_score, (int, float)) and risk_score >= 0.7


if _STARLETTE_AVAILABLE:

    class AnalyticsMiddleware(BaseHTTPMiddleware):
        """
        Automatic analytics collection middleware.

        Intercepts every response on the ``/analyze`` (or configurable)
        paths, decodes the JSON body, extracts analytics fields, and
        pushes a snapshot to AnalyticsService.

        Parameters
        ----------
        app:
            The ASGI application.
        analytics_service:
            Shared AnalyticsService instance.
        tracked_paths:
            URL prefixes that should trigger analytics collection.
            Default: ``["/analyze", "/pipeline"]``.
        """

        _DEFAULT_PATHS = ("/analyze", "/pipeline")

        def __init__(
            self,
            app,
            analytics_service: AnalyticsService,
            tracked_paths: tuple = _DEFAULT_PATHS,
        ) -> None:
            super().__init__(app)
            self._svc = analytics_service
            self._paths = tracked_paths

        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            path = request.url.path
            if not any(path.startswith(p) for p in self._paths):
                return await call_next(request)

            start = time.perf_counter()
            response: Response = await call_next(request)
            latency_ms = (time.perf_counter() - start) * 1000

            # Only collect on successful JSON responses
            if response.status_code == 200:
                await self._collect(response, latency_ms)

            return response

        async def _collect(self, response: Response, latency_ms: float) -> None:
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                # Rebuild body iterator so the client still receives the data
                async def _body_iter():
                    yield body

                response.body_iterator = _body_iter()

                payload = json.loads(body.decode())

                # If this is a ChatResponse, extract the nested AnalyzeResponse
                if isinstance(payload, dict) and "analysis" in payload:
                    payload = payload["analysis"]
                
                self._push_snapshot(payload, latency_ms)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                # Response body wasn't JSON (e.g. file export) — nothing to record.
                logger.debug("Analytics collection skipped: %s", exc)
            except Exception:
                # Any unexpected extraction error must never fail the request,
                # but it also must not be swallowed silently — surface it so
                # analytics gaps are noticed instead of quietly returning zeros.
                logger.warning(
                    "Analytics collection failed unexpectedly", exc_info=True
                )

        def _push_snapshot(self, payload: dict, latency_ms: float) -> None:
            risk_score = (
                payload.get("risk_score")
                or _as_dict(payload.get("risk")).get("score", 0.0)
                or 0.0
            )
            hallucination = _extract_hallucination_detected(payload)
            validation_success = _extract_validation_success(payload)
            alerts = _extract_alerts_generated(payload)
            high_risk = _extract_high_risk(payload, risk_score)
            pipeline_time = float(
                payload.get("pipeline_execution_time_ms")
                or payload.get("execution_time_ms")
                or latency_ms
            )

            snapshot = AnalyticsSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                latency_ms=round(latency_ms, 3),
                risk_score=float(risk_score),
                hallucination_detected=hallucination,
                validation_success=validation_success,
                alerts_generated=alerts,
                high_risk=high_risk,
                pipeline_execution_time_ms=round(pipeline_time, 3),
                correlation_id=get_correlation_id(),
            )
            self._svc.record(snapshot)
            logger.debug(
                "Analytics recorded | cid=%s | latency=%.1fms | risk=%.3f",
                snapshot.correlation_id,
                latency_ms,
                float(risk_score),
            )

else:  # pragma: no cover

    class AnalyticsMiddleware:  # type: ignore[no-redef]
        """Stub when Starlette is not installed."""

        def __init__(self, *args, **kwargs) -> None:
            raise ImportError("starlette is required for AnalyticsMiddleware")
