"""
memory_agent.py
---------------
Phase 7 — Memory Layer: MemoryAgent

Persists each pipeline session to the configured SessionStore after evaluation
and before alerting. Designed to be storage-backend-agnostic — swap
LocalJSONSessionStore for FirestoreSessionStore with zero agent code changes.

Pipeline position: Evaluator → Memory → Alert

Session record schema
---------------------
{
    "session_id":     str,
    "patient_id":     str,
    "query":          str,
    "ai_response":    str,
    "hallucinations": list[dict],   # HallucinationResult.model_dump()
    "risk_score":     float,
    "risk_level":     str,
    "risk_breakdown": dict | None,
    "safe_response":  str,
    "evaluation":     dict | None,  # EvaluationReport.model_dump()
    "timestamp":      str           # ISO 8601 UTC
}
"""

import time
import logging
from datetime import datetime, timezone

from backend.agents.base import BaseAgent
from backend.models.schemas import PipelineContext, AgentTrace, AgentMessage
from backend.memory import LocalJSONSessionStore, SessionStore

logger = logging.getLogger("clinguard.observability")


class MemoryAgent(BaseAgent):
    """
    Phase 7 — Persistent memory agent.

    Serialises the completed pipeline context and saves it to the configured
    SessionStore. Attaches the resulting session_id to context.metadata.

    Parameters
    ----------
    store : SessionStore | None
        Storage backend to use. Defaults to LocalJSONSessionStore.
        Inject a different implementation (e.g., FirestoreSessionStore) here
        without changing any other agent code.
    """

    def __init__(self, store: SessionStore | None = None) -> None:
        self._store: SessionStore = store or LocalJSONSessionStore()

    @property
    def agent_name(self) -> str:
        return "MemoryAgent"

    def process(self, context: PipelineContext) -> PipelineContext:
        start_time = time.perf_counter()
        logger.info("[MemoryAgent] started")

        status = "SUCCESS"
        session_id: str = ""

        try:
            # ----------------------------------------------------------------
            # Build session record
            # ----------------------------------------------------------------
            session: dict = {
                "patient_id": context.patient_id,
                "query": context.query,
                "ai_response": context.ai_response,
                "hallucinations": [
                    h.model_dump() for h in context.hallucinations
                ],
                "risk_score": context.risk_score,
                "risk_level": context.risk_level,
                "risk_breakdown": (
                    context.risk_breakdown.model_dump()
                    if context.risk_breakdown else None
                ),
                "safe_response": context.safe_response,
                "evaluation": (
                    context.evaluation_report.model_dump()
                    if context.evaluation_report else None
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "claims": [
                    c.model_dump() for c in context.claims
                ],

                "validations": [
                    v.model_dump() for v in context.validations
                ],

                "medical_entities": context.medical_entities,

                "alerts": [
                    a.model_dump() for a in context.alerts
                ],

                "metadata": context.metadata,

                "agent_traces": [
                    t.model_dump() for t in context.traces
                ]
            }

            # ----------------------------------------------------------------
            # Persist
            # ----------------------------------------------------------------
            session_id = self._store.save_session(session)
            context.metadata["session_id"] = session_id
            context.metadata["memory_saved"] = True

            logger.info(
                f"[MemoryAgent] session saved "
                f"session_id={session_id} "
                f"patient_id={context.patient_id}"
            )

        except Exception as exc:
            logger.error(f"[MemoryAgent] error: {exc}", exc_info=True)
            context.metadata["memory_error"] = str(exc)
            context.metadata["memory_saved"] = False
            status = "FAILED"

        # --------------------------------------------------------------------
        # A2A message to AlertAgent
        # --------------------------------------------------------------------
        msg = AgentMessage(
            sender=self.agent_name,
            receiver="AlertAgent",
            payload=(
                f"Session persisted. "
                f"session_id={session_id or 'N/A'} "
                f"patient_id={context.patient_id}."
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        context.metadata.setdefault("message_history", []).append(msg.model_dump())

        # --------------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------------
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"[MemoryAgent] completed time={elapsed:.2f}ms status={status}")

        trace = AgentTrace(
            agent_name=self.agent_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=elapsed,
            status=status,
        )
        context.traces.append(trace)
        return context
