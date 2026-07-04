"""
test_evaluator.py
-----------------
Unit tests for Phase 6 — Agent Self-Evaluation

Covers:
- Hallucination coverage scoring
- Validation consistency scoring
- Risk consistency scoring (HIGH/CRITICAL require emergency keywords)
- Safety completeness scoring (disclaimer, consultation, medication warning)
- Overall score calculation and PASS/FAIL threshold
- FAIL warning appended to safe_response
- EvaluationReport schema populated in context
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from backend.agents.evaluator_agent.evaluator_agent import EvaluatorAgent
from backend.models.schemas import (
    PipelineContext,
    HallucinationResult,
    ValidationResult,
    EvaluationReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_SAFE_RESPONSE = (
    "⚠️ IMPORTANT: This information is AI-generated and may not be accurate. "
    "Always consult a licensed healthcare professional before making any medical decisions. "
    "Do not start, stop, or modify medications based solely on AI-generated advice. "
    "Seek immediate medical evaluation. Call emergency services if symptoms are severe. "
    "Potentially unsafe medical information detected."
)

_POOR_SAFE_RESPONSE = "Just rest and drink water."


def _hal(is_hal=True, text="bad", details="hallucinated"):
    return HallucinationResult(
        is_hallucination=is_hal,
        detected_text=text,
        confidence_score=0.9,
        details=details,
    )


def _val(claim_id="c1", is_valid=True):
    return ValidationResult(
        claim_id=claim_id,
        is_valid=is_valid,
        source="test",
        confidence=0.9,
        reasoning="test",
    )


def _make_ctx(
    safe_response=_GOOD_SAFE_RESPONSE,
    risk_level="LOW",
    hallucinations=None,
    validations=None,
):
    ctx = PipelineContext(
        patient_id="p1",
        query="test",
        ai_response="original",
        safe_response=safe_response,
        risk_level=risk_level,
        hallucinations=hallucinations or [],
        validations=validations or [],
    )
    ctx.metadata["message_history"] = []
    return ctx


def _run(ctx):
    agent = EvaluatorAgent()
    return agent.process(ctx)


# ===========================================================================
# EvaluationReport Schema
# ===========================================================================

class TestEvaluationReportSchema:

    def test_report_stored_in_context(self):
        ctx = _make_ctx()
        result = _run(ctx)
        assert result.evaluation_report is not None
        assert isinstance(result.evaluation_report, EvaluationReport)

    def test_all_score_fields_present(self):
        ctx = _make_ctx()
        result = _run(ctx)
        r = result.evaluation_report
        assert hasattr(r, "coverage_score")
        assert hasattr(r, "consistency_score")
        assert hasattr(r, "risk_consistency_score")
        assert hasattr(r, "safety_score")
        assert hasattr(r, "overall_score")
        assert hasattr(r, "passed")

    def test_scores_in_valid_range(self):
        ctx = _make_ctx()
        result = _run(ctx)
        r = result.evaluation_report
        for score in [r.coverage_score, r.consistency_score,
                      r.risk_consistency_score, r.safety_score, r.overall_score]:
            assert 0.0 <= score <= 100.0

    def test_metadata_evaluation_report_serialised(self):
        ctx = _make_ctx()
        result = _run(ctx)
        assert "evaluation_report" in result.metadata
        assert isinstance(result.metadata["evaluation_report"], dict)


# ===========================================================================
# PASS / FAIL threshold
# ===========================================================================

class TestPassFailThreshold:

    def test_good_response_passes(self):
        ctx = _make_ctx(safe_response=_GOOD_SAFE_RESPONSE, risk_level="LOW")
        result = _run(ctx)
        assert result.evaluation_report.passed is True

    def test_poor_response_fails(self):
        ctx = _make_ctx(safe_response=_POOR_SAFE_RESPONSE, risk_level="HIGH")
        result = _run(ctx)
        assert result.evaluation_report.passed is False

    def test_fail_appends_warning_to_safe_response(self):
        ctx = _make_ctx(safe_response=_POOR_SAFE_RESPONSE, risk_level="CRITICAL")
        result = _run(ctx)
        if not result.evaluation_report.passed:
            assert "evaluation warning" in result.safe_response.lower()

    def test_pass_does_not_append_warning(self):
        ctx = _make_ctx(safe_response=_GOOD_SAFE_RESPONSE, risk_level="LOW")
        result = _run(ctx)
        if result.evaluation_report.passed:
            assert "evaluation warning" not in result.safe_response.lower()

    def test_overall_score_gte_80_is_pass(self):
        ctx = _make_ctx(safe_response=_GOOD_SAFE_RESPONSE, risk_level="LOW")
        result = _run(ctx)
        r = result.evaluation_report
        if r.overall_score >= 80:
            assert r.passed is True
        else:
            assert r.passed is False


# ===========================================================================
# Dimension 1: Hallucination Coverage
# ===========================================================================

class TestHallucinationCoverage:

    def test_no_hallucinations_perfect_coverage(self):
        ctx = _make_ctx(hallucinations=[])
        result = _run(ctx)
        assert result.evaluation_report.coverage_score == pytest.approx(100.0)

    def test_hallucination_acknowledged_in_response_scores_high(self):
        ctx = _make_ctx(
            safe_response=_GOOD_SAFE_RESPONSE + " Potentially unsafe information removed.",
            hallucinations=[_hal()],
        )
        result = _run(ctx)
        assert result.evaluation_report.coverage_score >= 80.0

    def test_unacknowledged_hallucination_reduces_score(self):
        ctx = _make_ctx(
            safe_response="Just rest and drink water. See a doctor.",
            hallucinations=[_hal(), _hal(text="another bad claim")],
        )
        result = _run(ctx)
        assert result.evaluation_report.coverage_score < 100.0


# ===========================================================================
# Dimension 2: Validation Consistency
# ===========================================================================

class TestValidationConsistency:

    def test_all_valid_claims_scores_100(self):
        ctx = _make_ctx(validations=[_val(is_valid=True)])
        result = _run(ctx)
        assert result.evaluation_report.consistency_score == pytest.approx(100.0)

    def test_invalid_claim_reflected_scores_well(self):
        ctx = _make_ctx(
            safe_response=_GOOD_SAFE_RESPONSE + " Some claims could not be verified. unsafe content removed.",
            validations=[_val(is_valid=False)],
        )
        result = _run(ctx)
        assert result.evaluation_report.consistency_score >= 70.0

    def test_invalid_claim_not_reflected_penalised(self):
        ctx = _make_ctx(
            safe_response="Just drink water.",
            validations=[_val(is_valid=False), _val(claim_id="c2", is_valid=False)],
        )
        result = _run(ctx)
        assert result.evaluation_report.consistency_score < 90.0


# ===========================================================================
# Dimension 3: Risk Consistency
# ===========================================================================

class TestRiskConsistency:

    def test_low_risk_always_full_score(self):
        ctx = _make_ctx(risk_level="LOW", safe_response="Drink water.")
        result = _run(ctx)
        assert result.evaluation_report.risk_consistency_score == pytest.approx(100.0)

    def test_critical_risk_with_emergency_content_scores_100(self):
        ctx = _make_ctx(
            risk_level="CRITICAL",
            safe_response=(
                "Call emergency services. Seek immediate medical evaluation. "
                "Consult a healthcare professional."
            ),
        )
        result = _run(ctx)
        assert result.evaluation_report.risk_consistency_score == pytest.approx(100.0)

    def test_critical_risk_without_emergency_content_penalised(self):
        ctx = _make_ctx(risk_level="CRITICAL", safe_response="Just rest.")
        result = _run(ctx)
        assert result.evaluation_report.risk_consistency_score < 80.0

    def test_moderate_risk_with_consultation_scores_high(self):
        ctx = _make_ctx(
            risk_level="MODERATE",
            safe_response="Please consult a physician for further evaluation.",
        )
        result = _run(ctx)
        assert result.evaluation_report.risk_consistency_score >= 80.0


# ===========================================================================
# Dimension 4: Safety Completeness
# ===========================================================================

class TestSafetyCompleteness:

    def test_full_disclaimer_and_consultation_scores_high(self):
        ctx = _make_ctx(safe_response=_GOOD_SAFE_RESPONSE)
        result = _run(ctx)
        assert result.evaluation_report.safety_score >= 70.0

    def test_missing_disclaimer_penalises_score(self):
        ctx = _make_ctx(safe_response="Just rest and drink water.")
        result = _run(ctx)
        # Safety score should be lower without disclaimer/consultation
        assert result.evaluation_report.safety_score < 100.0


# ===========================================================================
# Observability
# ===========================================================================

class TestEvaluatorObservability:

    def test_trace_added(self):
        ctx = _make_ctx()
        result = _run(ctx)
        names = [t.agent_name for t in result.traces]
        assert "EvaluatorAgent" in names

    def test_a2a_message_added(self):
        ctx = _make_ctx()
        result = _run(ctx)
        senders = [m["sender"] for m in result.metadata.get("message_history", [])]
        assert "EvaluatorAgent" in senders

    def test_evaluation_passed_in_metadata(self):
        ctx = _make_ctx()
        result = _run(ctx)
        assert "evaluation_passed" in result.metadata
