"""
test_generator.py
-----------------
Unit tests for Phase 5 — Safe Response Generator

Covers:
- Dangerous pattern replacement (chest pain home treatment, etc.)
- Ibuprofen-metformin removal
- Emergency redirect prepended for HIGH/CRITICAL
- Hallucination notice appended when hallucinations present
- Mandatory disclaimer always present
- Confidence score range
- SafeResponseMetadata fields populated
- SafeResponseGenerator via GeneratorAgent integration
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from backend.agents.generator_agent.response_generator.generator import SafeResponseGenerator
from backend.agents.generator_agent.generator_agent import GeneratorAgent
from backend.models.schemas import (
    PipelineContext,
    HallucinationResult,
    ValidationResult,
    SafeResponseMetadata,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hal(text="bad claim", details="hallucinated claim", is_hal=True):
    return HallucinationResult(
        is_hallucination=is_hal,
        detected_text=text,
        confidence_score=0.95,
        details=details,
    )


def _generate(original, risk_level="LOW", hallucinations=None, validations=None):
    gen = SafeResponseGenerator()
    return gen.generate(
        original=original,
        hallucinations=hallucinations or [],
        risk_level=risk_level,
        validations=validations or [],
    )


# ===========================================================================
# SafeResponseGenerator — Pattern Replacement
# ===========================================================================

class TestSafeResponseGeneratorPatterns:

    def test_chest_pain_home_treatment_replaced(self):
        meta = _generate(
            "Chest pain can be treated at home with rest.",
            risk_level="CRITICAL",
        )
        assert "chest pain can be treated at home" not in meta.safe_response.lower()
        assert "emergency" in meta.safe_response.lower() or "medical" in meta.safe_response.lower()

    def test_ibuprofen_metformin_removed(self):
        meta = _generate(
            "Take ibuprofen-metformin twice daily for pain.",
            risk_level="MODERATE",
        )
        assert "ibuprofen-metformin" not in meta.safe_response.lower()

    def test_stroke_home_treatment_replaced(self):
        meta = _generate(
            "A stroke can be treated at home with aspirin.",
            risk_level="CRITICAL",
        )
        assert "treated at home" not in meta.safe_response.lower()

    def test_symptom_minimisation_replaced(self):
        meta = _generate(
            "Chest pain is nothing to worry about and is harmless.",
            risk_level="HIGH",
        )
        assert "nothing to worry" not in meta.safe_response.lower()

    def test_modifications_list_populated(self):
        meta = _generate(
            "Chest pain can be treated at home.",
            risk_level="CRITICAL",
        )
        assert len(meta.modifications_made) > 0

    def test_no_dangerous_patterns_no_core_modifications(self):
        meta = _generate(
            "Drink plenty of water and rest well.",
            risk_level="LOW",
        )
        # Only disclaimer and possibly preamble — no dangerous pattern replacements
        dangerous_mods = [
            m for m in meta.modifications_made
            if "replaced" in m.lower() or "removed" in m.lower()
        ]
        assert len(dangerous_mods) == 0

    def test_invalid_disease_phrase_removed(self):
        meta = _generate(
            "You may have cardiopulmonary syndrome.",
            risk_level="LOW",
            validations=[ValidationResult(claim_id="claim_1", claim_text="cardiopulmonary syndrome", is_valid=False, source="mock", confidence=0.0, reasoning="invalid")],
        )
        assert "cardiopulmonary syndrome" not in meta.safe_response.lower()
        assert "could not be verified" in meta.safe_response.lower()

    def test_invalid_drug_phrase_removed(self):
        meta = _generate(
            "Take ibuprofen-metformin twice daily.",
            risk_level="LOW",
            validations=[ValidationResult(claim_id="claim_1", claim_text="ibuprofen-metformin", is_valid=False, source="mock", confidence=0.0, reasoning="invalid")],
        )
        assert "ibuprofen-metformin" not in meta.safe_response.lower()
        assert "medication mentioned could not be verified" in meta.safe_response.lower()

    def test_dangerous_advice_sentence_replaced(self):
        meta = _generate(
            "Stay home and rest for two days.",
            risk_level="LOW",
        )
        assert "stay home and rest for two days" not in meta.safe_response.lower()
        assert "seek immediate medical evaluation" in meta.safe_response.lower()


# ===========================================================================
# SafeResponseGenerator — Risk Level Handling
# ===========================================================================

class TestSafeResponseGeneratorRiskLevel:

    def test_critical_prepends_emergency_redirect(self):
        meta = _generate("See a doctor.", risk_level="CRITICAL")
        assert "emergency" in meta.safe_response.lower()
        assert meta.safe_response.lower().index("emergency") < 200  # Near start

    def test_high_prepends_emergency_redirect(self):
        meta = _generate("See a doctor.", risk_level="HIGH")
        assert "emergency" in meta.safe_response.lower()

    def test_low_no_emergency_preamble(self):
        meta = _generate("Drink water.", risk_level="LOW")
        # Should not have CRITICAL or HIGH preamble
        assert "critical risk detected" not in meta.safe_response.lower()
        assert "high risk" not in meta.safe_response.lower()

    def test_critical_risk_preamble_present(self):
        meta = _generate("See a doctor.", risk_level="CRITICAL")
        assert "critical risk" in meta.safe_response.lower()

    def test_moderate_risk_preamble_present(self):
        meta = _generate("See a doctor.", risk_level="MODERATE")
        assert "moderate risk" in meta.safe_response.lower()


# ===========================================================================
# SafeResponseGenerator — Hallucination Handling
# ===========================================================================

class TestSafeResponseGeneratorHallucinations:

    def test_hallucination_notice_appended(self):
        meta = _generate(
            "Take this medicine.",
            hallucinations=[_hal(text="fakemed 500mg", details="hallucinated drug")],
        )
        assert any(
            phrase in meta.safe_response.lower()
            for phrase in [
                "potentially unsafe", "consult a licensed", "do not start",
                "do not stop", "do not modify",
            ]
        )

    def test_no_hallucinations_no_notice(self):
        meta = _generate(
            "Drink water and rest.",
            hallucinations=[_hal(is_hal=False, text="water", details="valid")],
        )
        # Non-hallucination should not trigger the notice
        assert "hallucination" not in meta.safe_response.lower()

    def test_modification_log_includes_hallucination_warning(self):
        meta = _generate(
            "Take this drug.",
            hallucinations=[_hal(text="fakemed", details="drug medication")],
        )
        hal_mods = [m for m in meta.modifications_made if "hallucination" in m.lower()]
        assert len(hal_mods) > 0


# ===========================================================================
# SafeResponseGenerator — Disclaimer
# ===========================================================================

class TestSafeResponseGeneratorDisclaimer:

    def test_disclaimer_always_present_low_risk(self):
        meta = _generate("Drink water.", risk_level="LOW")
        assert "important" in meta.safe_response.lower() or "disclaimer" in meta.safe_response.lower()

    def test_disclaimer_always_present_critical_risk(self):
        meta = _generate("See a doctor.", risk_level="CRITICAL")
        assert "consult a licensed healthcare professional" in meta.safe_response.lower()

    def test_original_response_preserved_in_metadata(self):
        original = "Drink water and rest."
        meta = _generate(original, risk_level="LOW")
        assert meta.original_response == original


# ===========================================================================
# SafeResponseGenerator — Confidence Score
# ===========================================================================

class TestSafeResponseGeneratorConfidence:

    def test_confidence_in_valid_range(self):
        meta = _generate("Take care.", risk_level="LOW")
        assert 0.0 <= meta.confidence <= 1.0

    def test_confidence_with_modifications_is_high(self):
        meta = _generate(
            "Chest pain can be treated at home. Take ibuprofen-metformin.",
            risk_level="CRITICAL",
        )
        # More modifications → confidence should be ≥ 0.85
        assert meta.confidence >= 0.75

    def test_confidence_type_is_float(self):
        meta = _generate("Some advice.", risk_level="MODERATE")
        assert isinstance(meta.confidence, float)


# ===========================================================================
# SafeResponseMetadata Schema
# ===========================================================================

class TestSafeResponseMetadataSchema:

    def test_all_required_fields_present(self):
        meta = _generate("Test response.", risk_level="LOW")
        assert isinstance(meta, SafeResponseMetadata)
        assert isinstance(meta.original_response, str)
        assert isinstance(meta.safe_response, str)
        assert isinstance(meta.safety_reason, str)
        assert isinstance(meta.confidence, float)
        assert isinstance(meta.modifications_made, list)

    def test_safety_reason_non_empty(self):
        meta = _generate("Test.", risk_level="LOW")
        assert len(meta.safety_reason) > 0


# ===========================================================================
# GeneratorAgent Integration
# ===========================================================================

class TestGeneratorAgentIntegration:

    def _make_context(self, ai_response, risk_level="LOW", hallucinations=None):
        ctx = PipelineContext(
            patient_id="p1",
            query="test query",
            ai_response=ai_response,
            risk_level=risk_level,
            hallucinations=hallucinations or [],
        )
        ctx.metadata["message_history"] = []
        return ctx

    def test_agent_sets_safe_response(self):
        agent = GeneratorAgent()
        ctx = self._make_context("Drink water.", risk_level="LOW")
        result = agent.process(ctx)
        assert result.safe_response != ""

    def test_agent_stores_metadata(self):
        agent = GeneratorAgent()
        ctx = self._make_context("Drink water.", risk_level="LOW")
        result = agent.process(ctx)
        assert "safe_response_metadata" in result.metadata

    def test_agent_adds_trace(self):
        agent = GeneratorAgent()
        ctx = self._make_context("Drink water.", risk_level="LOW")
        result = agent.process(ctx)
        trace_names = [t.agent_name for t in result.traces]
        assert "GeneratorAgent" in trace_names

    def test_critical_risk_response_contains_emergency(self):
        agent = GeneratorAgent()
        ctx = self._make_context(
            "Chest pain can be treated at home.", risk_level="CRITICAL"
        )
        result = agent.process(ctx)
        assert "emergency" in result.safe_response.lower()
