"""
observability.py
----------------
Enterprise observability primitives for ClinGuard-AI Phase 10.

Provides:
- Correlation ID generation and propagation via contextvars
- Request / pipeline / agent span tracing with timing
- Structured log formatter that injects correlation_id into every record
- A FastAPI middleware that attaches a correlation ID to every request
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

# ---------------------------------------------------------------------------
# Context variable — propagated through async call chains automatically
# ---------------------------------------------------------------------------

_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the correlation ID for the current request context."""
    return _correlation_id_var.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current request context."""
    _correlation_id_var.set(cid)


def new_correlation_id() -> str:
    """Generate and set a new UUID4 correlation ID, returning it."""
    cid = str(uuid.uuid4())
    set_correlation_id(cid)
    return cid


# ---------------------------------------------------------------------------
# Structured log formatter
# ---------------------------------------------------------------------------


class CorrelationLogFormatter(logging.Formatter):
    """
    A log formatter that appends ``correlation_id`` to every record.

    Install once at application startup::

        handler = logging.StreamHandler()
        handler.setFormatter(CorrelationLogFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s [%(correlation_id)s] %(message)s"
        ))
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        record.correlation_id = get_correlation_id() or "-"
        return super().format(record)


# ---------------------------------------------------------------------------
# Span / trace models
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """A single named timing span within a trace."""

    name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return round((self.end_time - self.start_time) * 1000, 3)

    def finish(self, error: Optional[str] = None) -> None:
        self.end_time = time.perf_counter()
        if error:
            self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass
class Trace:
    """
    A complete request trace containing multiple spans.

    Created once per request and passed through the pipeline.
    """

    correlation_id: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    spans: List[Span] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start_span(self, name: str, **meta: Any) -> Span:
        span = Span(name=name, metadata=meta)
        self.spans.append(span)
        return span

    def finish(self) -> None:
        self.end_time = time.perf_counter()

    @property
    def total_duration_ms(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return round((self.end_time - self.start_time) * 1000, 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "total_duration_ms": self.total_duration_ms,
            "spans": [s.to_dict() for s in self.spans],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------


class Tracer:
    """
    Lightweight request tracer.

    Usage::

        tracer = Tracer()
        trace = tracer.start_trace()
        with tracer.span(trace, "RiskScoringAgent"):
            ...  # agent work
        tracer.finish_trace(trace)
    """

    def __init__(self, logger_name: str = "clinguard.tracer") -> None:
        self._log = logging.getLogger(logger_name)

    def start_trace(self, **meta: Any) -> Trace:
        cid = get_correlation_id() or new_correlation_id()
        trace = Trace(correlation_id=cid, metadata=meta)
        self._log.debug("Trace started | correlation_id=%s", cid)
        return trace

    def finish_trace(self, trace: Trace) -> None:
        trace.finish()
        self._log.debug(
            "Trace finished | correlation_id=%s | duration_ms=%s",
            trace.correlation_id,
            trace.total_duration_ms,
        )

    @contextmanager
    def span(
        self, trace: Trace, name: str, **meta: Any
    ) -> Generator[Span, None, None]:
        """Context manager that starts and finishes a span."""
        s = trace.start_span(name, **meta)
        try:
            yield s
        except Exception as exc:
            s.finish(error=str(exc))
            raise
        else:
            s.finish()


# ---------------------------------------------------------------------------
# FastAPI middleware
# ---------------------------------------------------------------------------


try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class CorrelationIdMiddleware(BaseHTTPMiddleware):
        """
        Starlette / FastAPI middleware that:

        1. Reads ``X-Correlation-ID`` from incoming request headers (or
           generates a new one).
        2. Sets it in the ``contextvars`` context so it flows through the
           entire request lifecycle.
        3. Echoes it back in the response via ``X-Correlation-ID``.
        """

        HEADER = "X-Correlation-ID"

        async def dispatch(self, request: Request, call_next) -> Response:
            cid = request.headers.get(self.HEADER) or new_correlation_id()
            set_correlation_id(cid)
            response: Response = await call_next(request)
            response.headers[self.HEADER] = cid
            return response

except ImportError:  # pragma: no cover
    # Starlette not installed — middleware unavailable but rest of module works
    class CorrelationIdMiddleware:  # type: ignore[no-redef]
        pass
