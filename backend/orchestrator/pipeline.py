"""
pipeline.py
-----------
ClinGuard AI — Main Pipeline Orchestrator

Pipeline execution order (Phase 4–7 update):
  1. InterceptorAgent  — request validation & context init
  2. DetectorAgent     — hallucination detection
  3. ValidatorAgent    — claim validation (disease / drug / evidence)
  4. RiskAgent         — risk intelligence engine (severity × urgency × vulnerability)
  5. GeneratorAgent    — safe response generation
  6. EvaluatorAgent    — agent self-evaluation (0–100 score, PASS/FAIL)
  7. MemoryAgent       — persistent session storage
  8. AlertAgent        — alert generation for HIGH/CRITICAL risk
"""

from backend.models.schemas import AnalyzeRequest, AnalyzeResponse, PipelineContext
from backend.agents import (
    InterceptorAgent,
    DetectorAgent,
    ValidatorAgent,
    RiskAgent,
    GeneratorAgent,
    EvaluatorAgent,
    MemoryAgent,
    AlertAgent,
)
from backend.explainability import (
    AuditRepository,
    AuditService,
    ExplanationEngine,
    TimelineEngine,
)
from backend.services import (
    AuditServiceV2,
    ExplanationEngineV2,
    TimelineEngineV2,
    DecisionTraceEngine,
)
from backend.repositories import AuditRepositoryV2


class ClinGuardPipeline:
    def __init__(self) -> None:
        self.agents = [
            InterceptorAgent(),
            DetectorAgent(),
            ValidatorAgent(),
            RiskAgent(),
            GeneratorAgent(),
            EvaluatorAgent(),
            MemoryAgent(),
            AlertAgent(),
        ]
        # V1
        self.explanation_engine = ExplanationEngine()
        self.timeline_engine = TimelineEngine()
        self.audit_service = AuditService()
        self.audit_repository = AuditRepository()
        
        # V2 (Phase 9)
        self.explanation_engine_v2 = ExplanationEngineV2()
        self.timeline_engine_v2 = TimelineEngineV2()
        self.decision_trace_engine = DecisionTraceEngine()
        self.audit_service_v2 = AuditServiceV2(
            explanation_engine=self.explanation_engine_v2,
            timeline_engine=self.timeline_engine_v2,
            decision_trace_engine=self.decision_trace_engine
        )
        self.audit_repository_v2 = AuditRepositoryV2()

    def run(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """
        Execute all agents sequentially on the given request context.
        Returns a fully populated AnalyzeResponse.
        """
        context = PipelineContext(
            patient_id=request.patient_id,
            query=request.query,
            ai_response=request.ai_response,
            patient_age=request.patient_age,
            comorbidities=request.comorbidities,
        )

        for agent in self.agents:
            try:
                context = agent.process(context)
            except Exception as exc:
                context.metadata.setdefault("pipeline_errors", []).append(
                    {
                        "agent": agent.agent_name,
                        "error": str(exc),
                    }
                )
                raise

        # V1 execution
        explanations = self.explanation_engine.generate(context)
        agent_timeline = self.timeline_engine.timeline(context)
        decision_trace = self.timeline_engine.decision_trace(context)
        risk_explanation = self.audit_service.risk_explanation(context)
        audit_report = self.audit_service.build_report(
            context=context,
            explanations=explanations,
            timeline=agent_timeline,
            decision_trace=decision_trace,
        )
        self.audit_repository.save(audit_report)
        
        # V2 execution (Phase 9)
        audit_report_v2 = self.audit_service_v2.build_report(context=context)
        if audit_report_v2:
            self.audit_repository_v2.save_report(audit_report_v2)

        memory_saved: bool = context.metadata.get("memory_saved", False)

        return AnalyzeResponse(
            version="0.3.0",
            risk_level=context.risk_level,
            risk_score=context.risk_score,
            risk_breakdown=context.risk_breakdown,
            hallucinations=context.hallucinations,
            hallucination_detected=context.hallucination_detected,
            validated_claims=context.validations,
            safe_response=context.safe_response,
            evaluation_report=context.evaluation_report,
            alerts=context.alerts,
            traces=context.traces,
            memory_saved=memory_saved,
            medical_entities=context.medical_entities,
            explanations=explanations,
            agent_timeline=agent_timeline,
            decision_trace=decision_trace,
            risk_explanation=risk_explanation,
            audit_report=audit_report,
            audit_exports={
                "json": f"/audit/{audit_report.session_id}/export/json",
                "pdf": f"/audit/{audit_report.session_id}/export/pdf",
            },
            phase9_audit=audit_report_v2.model_dump(),
        )