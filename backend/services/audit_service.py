"""
audit_service.py
----------------
Phase 9 — Audit Report Assembler

Orchestrates ExplanationEngineV2, TimelineEngineV2, and
DecisionTraceEngine to assemble a complete ``AuditReport`` after
every pipeline execution.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from backend.models.audit import (
    AuditReport,
    ClaimExplanation,
    DecisionTrace,
    TimelineEvent,
)
from backend.models.schemas import PipelineContext
from backend.services.explanation_engine import ExplanationEngineV2
from backend.services.timeline_engine import TimelineEngineV2
from backend.services.decision_trace_engine import DecisionTraceEngine

logger = logging.getLogger("clinguard.phase9.audit")


class AuditServiceV2:
    """Build a fully-populated AuditReport from a completed PipelineContext."""

    def __init__(
        self,
        explanation_engine: ExplanationEngineV2 | None = None,
        timeline_engine: TimelineEngineV2 | None = None,
        decision_trace_engine: DecisionTraceEngine | None = None,
    ) -> None:
        self._explanation = explanation_engine or ExplanationEngineV2()
        self._timeline = timeline_engine or TimelineEngineV2()
        self._decision_trace = decision_trace_engine or DecisionTraceEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_report(self, context: PipelineContext) -> AuditReport:
        """
        Assemble an AuditReport encompassing all pipeline artefacts.

        Parameters
        ----------
        context : PipelineContext
            A *completed* pipeline context (all agents have run).

        Returns
        -------
        AuditReport
            The assembled report ready for persistence and export.
        """
        logger.info(
            "audit_service.build_report started patient_id=%s",
            context.patient_id,
        )
        now = datetime.now(timezone.utc).isoformat()

        explanations: List[ClaimExplanation] = self._explanation.generate(context)
        timeline: List[TimelineEvent] = self._timeline.generate(context)
        decision_traces: List[DecisionTrace] = self._decision_trace.generate(context)

        session_id: str = context.metadata.get("session_id", "session_unsaved")

        # Build risk assessment dict
        risk_assessment = context.metadata.get("risk_assessment")

        if hasattr(risk_assessment, "model_dump"):
            risk_assessment = risk_assessment.model_dump(mode="json")

        if not risk_assessment:
            risk_assessment = {
                "risk_level": context.risk_level,
                "risk_score": context.risk_score,
            }

            if context.risk_breakdown:
                risk_assessment.update(
                    context.risk_breakdown.model_dump(mode="json")
                )
        # Build pipeline timing
        pipeline_started_at: str | None = None
        pipeline_completed_at: str | None = None
        if timeline:
            pipeline_started_at = timeline[0].start_time
            pipeline_completed_at = timeline[-1].end_time

        report = AuditReport(
            session_id=session_id,
            patient_id=context.patient_id,
            timestamp=now,
            session_metadata={
                "session_id": session_id,
                "query": context.query,
                "ai_response": context.ai_response,
            },
            patient_information={
                "patient_id": context.patient_id,
                "patient_age": context.patient_age,
                "comorbidities": context.comorbidities,
            },
            medical_entities=context.medical_entities,
            hallucinations=[h.model_dump(mode="json") for h in context.hallucinations],
            validated_claims=[v.model_dump(mode="json") for v in context.validations],
            explanations=explanations,
            risk_assessment=risk_assessment,
            safe_response=context.safe_response,
            evaluation_report=(
                context.evaluation_report.model_dump(mode="json")
                if context.evaluation_report
                else None
            ),
            alerts=[a.model_dump(mode="json") for a in context.alerts],
            timeline=timeline,
            decision_trace=decision_traces,
            pipeline_started_at=pipeline_started_at,
            pipeline_completed_at=pipeline_completed_at,
        )

        logger.info(
            "audit_service.build_report completed session_id=%s "
            "explanations=%d timeline=%d decisions=%d",
            session_id,
            len(explanations),
            len(timeline),
            len(decision_traces),
        )
        context.metadata["audit_report"] = report.model_dump(mode="json")
        context.metadata["audit_session_id"] = session_id

        return report
