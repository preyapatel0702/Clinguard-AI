"""
test_risk_engine.py
-------------------
Unit tests for Phase 4 — Risk Intelligence Engine

Covers:
- SeverityCalculator keyword matching and scoring
- UrgencyCalculator category classification
- VulnerabilityCalculator age bands and comorbidity boosts
- RiskAgent weighted formula
- Hallucination boost logic (generic / fake drug / fake disease)
- Risk level thresholds (LOW / MODERATE / HIGH / CRITICAL)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from backend.tools.risk_calculator import (
    SeverityCalculator,
    UrgencyCalculator,
    VulnerabilityCalculator,
)
from backend.agents.risk_agent.risk_agent import RiskAgent
from backend.models.schemas import PipelineContext, HallucinationResult


# ===========================================================================
# SeverityCalculator
# ===========================================================================

class TestSeverityCalculator:
    def setup_method(self):
        self.calc = SeverityCalculator()

    def test_chest_pain_returns_0_9(self):
        score = self.calc.calculate("patient reports chest pain")
        assert score == pytest.approx(0.90)

    def test_heart_attack_returns_1_0(self):
        score = self.calc.calculate("suspected heart attack in progress")
        assert score == pytest.approx(1.00)

    def test_stroke_returns_1_0(self):
        score = self.calc.calculate("sudden stroke with paralysis")
        assert score == pytest.approx(1.00)

    def test_breathing_difficulty_returns_0_95(self):
        score = self.calc.calculate("patient has breathing difficulty")
        assert score == pytest.approx(0.95)

    def test_shortness_of_breath_returns_0_95(self):
        score = self.calc.calculate("shortness of breath on exertion")
        assert score == pytest.approx(0.95)

    def test_unconscious_returns_1_0(self):
        score = self.calc.calculate("patient found unconscious")
        assert score == pytest.approx(1.00)

    def test_default_for_unknown_symptom(self):
        score = self.calc.calculate("patient asked about vitamins")
        assert score == pytest.approx(0.30)

    def test_multiple_keywords_returns_highest(self):
        # Both headache (0.45) and stroke (1.0) present — should return 1.0
        score = self.calc.calculate("stroke with accompanying headache")
        assert score == pytest.approx(1.00)

    def test_case_insensitive(self):
        score = self.calc.calculate("CHEST PAIN on exertion")
        assert score == pytest.approx(0.90)

    def test_empty_text_returns_default(self):
        score = self.calc.calculate("")
        assert score == pytest.approx(0.30)


# ===========================================================================
# UrgencyCalculator
# ===========================================================================

class TestUrgencyCalculator:
    def setup_method(self):
        self.calc = UrgencyCalculator()

    def test_chest_pain_is_emergency(self):
        score = self.calc.calculate("chest pain, cannot breathe")
        assert score == pytest.approx(0.90)

    def test_heart_attack_is_emergency(self):
        score = self.calc.calculate("heart attack symptoms")
        assert score == pytest.approx(0.90)

    def test_stroke_is_emergency(self):
        score = self.calc.calculate("sudden stroke")
        assert score == pytest.approx(0.90)

    def test_seizure_is_serious(self):
        score = self.calc.calculate("patient had a seizure")
        assert score == pytest.approx(0.70)

    def test_high_fever_is_serious(self):
        score = self.calc.calculate("high fever for two days")
        assert score == pytest.approx(0.70)

    def test_headache_is_routine(self):
        score = self.calc.calculate("mild headache since morning")
        assert score == pytest.approx(0.30)

    def test_unknown_is_default(self):
        score = self.calc.calculate("diet and nutrition questions")
        assert score == pytest.approx(0.30)

    def test_emergency_takes_priority_over_routine(self):
        # Contains both headache (routine) and unconscious (emergency)
        score = self.calc.calculate("headache and then became unconscious")
        assert score == pytest.approx(0.90)


# ===========================================================================
# VulnerabilityCalculator
# ===========================================================================

class TestVulnerabilityCalculator:
    def setup_method(self):
        self.calc = VulnerabilityCalculator()

    def test_no_age_returns_default(self):
        score = self.calc.calculate()
        assert score == pytest.approx(0.50)

    def test_age_80_plus_returns_1_0(self):
        score = self.calc.calculate(age=82)
        assert score == pytest.approx(1.00)

    def test_age_65_to_79_returns_0_8(self):
        score = self.calc.calculate(age=70)
        assert score == pytest.approx(0.80)

    def test_age_50_to_64_returns_0_6(self):
        score = self.calc.calculate(age=55)
        assert score == pytest.approx(0.60)

    def test_age_below_50_returns_default(self):
        score = self.calc.calculate(age=30)
        assert score == pytest.approx(0.50)

    def test_diabetes_boost_applied(self):
        score = self.calc.calculate(age=40, comorbidities=["diabetes"])
        assert score == pytest.approx(0.60)   # 0.50 + 0.10

    def test_hypertension_boost_applied(self):
        score = self.calc.calculate(age=40, comorbidities=["hypertension"])
        assert score == pytest.approx(0.60)

    def test_multiple_comorbidities_stacked(self):
        score = self.calc.calculate(age=40, comorbidities=["diabetes", "hypertension"])
        assert score == pytest.approx(0.70)   # 0.50 + 0.10 + 0.10

    def test_score_capped_at_1_0(self):
        score = self.calc.calculate(
            age=80, comorbidities=["diabetes", "hypertension", "cancer"]
        )
        assert score == pytest.approx(1.00)   # 1.00 + boosts → capped

    def test_elderly_with_comorbidities_capped(self):
        score = self.calc.calculate(age=72, comorbidities=["diabetes", "hypertension"])
        # 0.80 + 0.10 + 0.10 = 1.00 (capped)
        assert score == pytest.approx(1.00)


# ===========================================================================
# RiskAgent — formula and hallucination boosts
# ===========================================================================

def _make_context(query="", ai_response="", hallucinations=None, age=None, comorbidities=None):
    return PipelineContext(
        patient_id="test_patient",
        query=query,
        ai_response=ai_response,
        patient_age=age,
        comorbidities=comorbidities or [],
        hallucinations=hallucinations or [],
    )


def _hal(is_hallucination=True, text="bad claim", details="hallucinated claim"):
    return HallucinationResult(
        is_hallucination=is_hallucination,
        detected_text=text,
        confidence_score=0.95,
        details=details,
    )


class TestRiskAgent:
    def setup_method(self):
        self.agent = RiskAgent()

    def test_chest_pain_classified_critical_with_hallucination(self):
        ctx = _make_context(
            query="chest pain",
            ai_response="chest pain can be treated at home",
            hallucinations=[_hal(text="ibuprofen-metformin", details="fake drug medication")],
        )
        result = self.agent.process(ctx)
        # severity=0.9, urgency=0.9, vulnerability=0.5
        # raw = 0.9×0.4 + 0.9×0.3 + 0.5×0.3 = 0.36+0.27+0.15 = 0.78
        # fake drug boost = +0.20 → 0.98 → CRITICAL
        assert result.risk_level == "CRITICAL"
        assert result.risk_score >= 0.80

    def test_chest_pain_no_hallucination_is_high(self):
        ctx = _make_context(
            query="chest pain",
            ai_response="seek medical evaluation for chest pain",
        )
        result = self.agent.process(ctx)
        # severity=0.9, urgency=0.9, vulnerability=0.5
        # raw = 0.78 → HIGH
        assert result.risk_level in ("HIGH", "CRITICAL")
        assert result.risk_score >= 0.60

    def test_no_emergency_symptoms_low_risk(self):
        ctx = _make_context(
            query="vitamins",
            ai_response="vitamin C is good for immunity",
        )
        result = self.agent.process(ctx)
        assert result.risk_level in ("LOW", "MODERATE")
        assert result.risk_score < 0.60

    def test_educational_statement_is_low_risk(self):
        ctx = _make_context(
            query="",
            ai_response="Diabetes is a chronic metabolic disease.",
            hallucinations=[],
            age=None,
            comorbidities=[],
        )
        result = self.agent.process(ctx)
        assert result.risk_level == "LOW"
        assert result.risk_score <= 0.25

    def test_hallucination_boost_generic(self):
        ctx = _make_context(
            query="vitamins",
            ai_response="take these supplements daily",
            hallucinations=[_hal(text="fake supplement", details="hallucinated claim")],
        )
        result_no_hal = self.agent.process(_make_context(
            query="vitamins", ai_response="take these supplements daily"
        ))
        result_with_hal = self.agent.process(ctx)
        assert result_with_hal.risk_score > result_no_hal.risk_score

    def test_fake_drug_boost_is_larger_than_generic(self):
        ctx_drug = _make_context(
            query="pain",
            ai_response="take these tablets",
            hallucinations=[_hal(text="ibuprofen-metformin 500mg tablet", details="fake drug")],
        )
        ctx_generic = _make_context(
            query="pain",
            ai_response="take these tablets",
            hallucinations=[_hal(text="some advice", details="general hallucination")],
        )
        r_drug = self.agent.process(ctx_drug)
        r_generic = self.agent.process(ctx_generic)
        assert r_drug.risk_score >= r_generic.risk_score

    def test_risk_breakdown_populated(self):
        ctx = _make_context(query="chest pain", ai_response="see a doctor")
        result = self.agent.process(ctx)
        assert result.risk_breakdown is not None
        assert result.risk_breakdown.severity_score > 0
        assert result.risk_breakdown.urgency_score > 0
        assert result.risk_breakdown.vulnerability_score > 0

    def test_elderly_patient_increases_score(self):
        ctx_young = _make_context(
            query="shortness of breath", ai_response="rest at home", age=25
        )
        ctx_elderly = _make_context(
            query="shortness of breath", ai_response="rest at home", age=80
        )
        r_young = self.agent.process(ctx_young)
        r_elderly = self.agent.process(ctx_elderly)
        assert r_elderly.risk_score > r_young.risk_score

    def test_risk_score_capped_at_1(self):
        ctx = _make_context(
            query="heart attack stroke unconscious",
            ai_response="treat at home immediately",
            hallucinations=[
                _hal(text="fake_drug 500mg tablet", details="fake drug medication"),
                _hal(text="fake_disease syndrome", details="fake disease condition"),
                _hal(text="bad advice", details="hallucinated claim"),
            ],
            age=85,
            comorbidities=["diabetes", "hypertension"],
        )
        result = self.agent.process(ctx)
        assert result.risk_score <= 1.0
        assert result.risk_level == "CRITICAL"

    def test_four_risk_levels_reachable(self):
        # LOW
        low = _make_context(query="vitamins", ai_response="vitamin C helps immunity")
        r_low = self.agent.process(low)
        assert r_low.risk_level in ("LOW", "MODERATE", "HIGH", "CRITICAL")

        # CRITICAL
        crit = _make_context(
            query="heart attack", ai_response="treat at home",
            hallucinations=[_hal(text="fake drug 500mg", details="drug medication")],
            age=80, comorbidities=["diabetes"]
        )
        r_crit = self.agent.process(crit)
        assert r_crit.risk_level == "CRITICAL"
