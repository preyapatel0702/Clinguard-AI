import logging
from datetime import datetime, timezone

from backend.models.schemas import (
    AuditReport,
    ClaimExplanation,
    DecisionTrace,
    PipelineContext,
    RiskExplanation,
    AgentTimelineEvent,
)


logger = logging.getLogger("clinguard.observability")


class AuditService:
    def risk_explanation(self, context: PipelineContext) -> RiskExplanation:
        breakdown = context.risk_breakdown
        risk_assessment = context.metadata.get("risk_assessment", {})
        narrative = risk_assessment.get("reasoning") or self._default_risk_narrative(context)

        if breakdown is None:
            return RiskExplanation(
                final_score=context.risk_score,
                risk_level=context.risk_level,
                narrative=narrative,
            )

        return RiskExplanation(
            severity_score=breakdown.severity_score,
            urgency_score=breakdown.urgency_score,
            vulnerability_score=breakdown.vulnerability_score,
            hallucination_boost=breakdown.hallucination_boost,
            raw_score=breakdown.raw_score,
            final_score=breakdown.final_score,
            risk_level=breakdown.risk_level,
            narrative=narrative,
        )

    def build_report(
        self,
        context: PipelineContext,
        explanations: list[ClaimExplanation],
        timeline: list[AgentTimelineEvent],
        decision_trace: DecisionTrace,
    ) -> AuditReport:
        logger.info("phase9.audit_creation started patient_id=%s", context.patient_id)
        session_id = context.metadata.get("session_id") or "session_unsaved"
        report = AuditReport(
            session_id=session_id,
            patient_id=context.patient_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            patient_context={
                "patient_id": context.patient_id,
                "query": context.query,
                "patient_age": context.patient_age,
                "comorbidities": context.comorbidities,
            },
            detected_entities=context.medical_entities,
            detected_hallucinations=context.hallucinations,
            validation_results=context.validations,
            explanations=explanations,
            risk_assessment=self.risk_explanation(context),
            generated_safe_response=context.safe_response,
            evaluation_metrics=context.evaluation_report,
            alerts=context.alerts,
            agent_timeline=timeline,
            decision_trace=decision_trace,
        )
        logger.info(
            "phase9.audit_creation completed session_id=%s validations=%s",
            session_id,
            len(context.validations),
        )
        return report

    def _default_risk_narrative(self, context: PipelineContext) -> str:
        unsupported = [validation for validation in context.validations if not validation.is_valid]
        if unsupported:
            return (
                f"Risk increased because {len(unsupported)} validation result(s) "
                "could not be medically supported."
            )
        if context.hallucinations:
            return "Risk increased because hallucinated or unsafe medical content was detected."
        return "Risk reflects symptom severity, urgency, patient vulnerability, and validation outcomes."
