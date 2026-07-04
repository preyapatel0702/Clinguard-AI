from pathlib import Path
from datetime import datetime, timezone
import pytest

from backend.services import (
    ExplanationEngineV2,
    TimelineEngineV2,
    DecisionTraceEngine,
    AuditServiceV2,
    PdfExportService,
)
from backend.repositories import AuditRepositoryV2
from backend.models.schemas import (
    PipelineContext,
    ValidationResult,
    HallucinationResult,
    RiskBreakdown,
    AgentTrace,
    EvaluationReport,
    AlertPayload,
)


def _context() -> PipelineContext:
    ctx = PipelineContext(
        patient_id="patient_1",
        query="Can metformin treat diabetes?",
        ai_response="Metformin is used to treat diabetes.",
        medical_entities={
            "drugs": [{"text": "metformin", "label": "Medication", "score": 0.998}],
            "diseases": [{"text": "diabetes", "label": "Disease_disorder", "score": 1.0}],
            "symptoms": [],
        },
        validations=[
            ValidationResult(
                claim_id="kb_metformin_diabetes",
                claim_text="metformin treats diabetes",
                is_valid=True,
                source="Medical Knowledge Base",
                confidence=0.95,
                reasoning="Drug-disease relationship supported by medical knowledge base.",
            )
        ],
        hallucinations=[
            HallucinationResult(
                is_hallucination=False,
                detected_text="",
                confidence_score=0.0,
                details="No hallucination detected.",
            ),
            HallucinationResult(
                is_hallucination=True,
                detected_text="FakeDrug",
                confidence_score=0.99,
                details="Flagged as non-existent drug.",
            )
        ],
        risk_score=0.4,
        risk_level="MODERATE",
        risk_breakdown=RiskBreakdown(
            severity_score=0.3,
            urgency_score=0.3,
            vulnerability_score=0.5,
            hallucination_boost=0.2,
            raw_score=0.2,
            final_score=0.4,
            risk_level="MODERATE",
        ),
        safe_response="Metformin is commonly used for diabetes. Consult a clinician.",
        traces=[
            AgentTrace(
                agent_name="DetectorAgent",
                timestamp="2026-06-21T10:00:00Z",
                execution_time_ms=12.5,
                status="SUCCESS",
            ),
            AgentTrace(
                agent_name="ValidatorAgent",
                timestamp="2026-06-21T10:00:01Z",
                execution_time_ms=8.0,
                status="SUCCESS",
            ),
        ],
        alerts=[
            AlertPayload(
                alert_id="alert_1",
                severity="HIGH",
                message="Elevated clinical risk detected",
                timestamp="2026-06-21T10:00:02Z",
            )
        ],
        evaluation_report=EvaluationReport(
            coverage_score=90,
            consistency_score=100,
            risk_consistency_score=80,
            safety_score=95,
            overall_score=91,
            passed=True,
            failure_reasons=[],
        ),
        metadata={
            "session_id": "session_test_v2",
            "message_history": [],
            "risk_assessment": {
                "risk_level": "MODERATE",
                "risk_score": 0.4,
                "reasoning": "Test risk reasoning.",
            },
            "safe_response_metadata": {
                "modifications_made": ["Added disclaimer."],
                "safety_reason": "Risk is MODERATE.",
                "confidence": 0.9,
            },
            "memory_saved": True,
        },
    )
    return ctx


def test_explanation_engine_v2():
    engine = ExplanationEngineV2()
    ctx = _context()
    explanations = engine.generate(ctx)

    assert len(explanations) == 4
    categories = [e.category for e in explanations]
    assert "hallucination_detection" in categories
    assert "validation_outcome" in categories
    assert "risk_calculation" in categories
    assert "response_modification" in categories

    for e in explanations:
        assert e.explanation_id.startswith("expl_")
        assert e.title
        assert e.reasoning
        assert 0.0 <= e.confidence <= 1.0


def test_timeline_engine_v2():
    engine = TimelineEngineV2()
    ctx = _context()
    timeline = engine.generate(ctx)

    assert len(timeline) == 2
    assert timeline[0].agent_name == "DetectorAgent"
    assert timeline[1].agent_name == "ValidatorAgent"
    assert "Extracted medical entities" in timeline[0].actions_performed[0]
    assert "Validated 1 claim(s)" in timeline[1].actions_performed[0]


def test_decision_trace_engine():
    engine = DecisionTraceEngine()
    ctx = _context()
    traces = engine.generate(ctx)

    assert len(traces) > 0
    actions = [t.action for t in traces]
    assert "extracted_medication" in actions
    assert "hallucination_detected" in actions
    assert "validated_claim" in actions
    assert "calculated_severity" in actions
    assert "modified_response" in actions


def test_audit_service_v2():
    ctx = _context()
    service = AuditServiceV2()
    report = service.build_report(ctx)

    assert report.session_id == "session_test_v2"
    assert report.patient_id == "patient_1"
    assert len(report.explanations) == 4
    assert len(report.timeline) == 2
    assert len(report.decision_trace) > 0


def test_audit_repository_v2_crud(tmp_path: Path):
    repo = AuditRepositoryV2(tmp_path / "audits_v2.json")
    ctx = _context()
    report = AuditServiceV2().build_report(ctx)

    # Create
    repo.save_report(report)

    # Read
    stored = repo.get_report("session_test_v2")
    assert stored is not None
    assert stored["session_id"] == "session_test_v2"

    # List history
    history = repo.get_patient_history("patient_1")
    assert len(history) == 1
    assert history[0].session_id == "session_test_v2"
    assert history[0].claim_count == 1

    # Delete
    deleted = repo.delete_report("session_test_v2")
    assert deleted is True
    assert repo.get_report("session_test_v2") is None


def test_pdf_export_service():
    ctx = _context()
    report = AuditServiceV2().build_report(ctx)
    pdf_service = PdfExportService()

    pdf_bytes = pdf_service.to_pdf_bytes(report)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"ClinGuard" in pdf_bytes
