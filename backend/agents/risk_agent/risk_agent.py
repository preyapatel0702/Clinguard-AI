"""
risk_agent.py
-------------
Phase 4 — Risk Intelligence Engine

Computes a clinically meaningful risk score using:
  risk_score = (severity * 0.4) + (urgency * 0.3) + (vulnerability * 0.3)

Then applies hallucination boosts:
  generic hallucination  → +0.15
  fake drug              → +0.20
  fake disease           → +0.10

Educational content shortcut (Issue 2):
  If ALL of the following are true:
    - hallucinations count = 0
    - invalid claims count = 0
    - no emergency symptoms detected in text
    - no dangerous advice detected in text
  Then risk_level = LOW and risk_score <= 0.25 (bypasses weighted formula).

Risk level thresholds:
  < 0.30              → LOW
  0.30 – 0.59         → MODERATE
  0.60 – 0.79         → HIGH
  >= 0.80             → CRITICAL
"""

import time
import logging
from datetime import datetime, timezone

from backend.agents.base import BaseAgent
from backend.models.schemas import (
    PipelineContext,
    AgentTrace,
    AgentMessage,
    RiskAssessment,
    RiskBreakdown,
)
from backend.tools.risk_calculator import (
    SeverityCalculator,
    UrgencyCalculator,
    VulnerabilityCalculator,
)

logger = logging.getLogger("clinguard.observability")

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
_THRESHOLDS: list[tuple[float, str]] = [
    (0.80, "CRITICAL"),
    (0.60, "HIGH"),
    (0.30, "MODERATE"),
    (0.00, "LOW"),
]

# Hallucination boost values
_BOOST_GENERIC: float = 0.15
_BOOST_FAKE_DRUG: float = 0.20
_BOOST_FAKE_DISEASE: float = 0.10


def _resolve_risk_level(score: float) -> str:
    for threshold, level in _THRESHOLDS:
        if score >= threshold:
            return level
    return "LOW"


def _compute_hallucination_boost(hallucinations: list) -> tuple[float, list[str]]:
    """
    Return total boost and list of reasons from detected hallucinations.
    Inspects hallucination `details` field for drug/disease clues.
    """
    boost = 0.0
    reasons: list[str] = []

    for h in hallucinations:
        if not h.is_hallucination:
            continue

        details_lower = h.details.lower()
        detected_lower = h.detected_text.lower()

        if (
            any(
                kw in details_lower
                for kw in ["drug", "medication", "medicine", "pharmaceutical"]
            )
            or any(
                kw in detected_lower
                for kw in ["drug", "medication", "mg", "tablet", "capsule", "dose"]
            )
        ):
            boost += _BOOST_FAKE_DRUG
            reasons.append(f"Fake/invalid drug detected: '{h.detected_text}' (+{_BOOST_FAKE_DRUG})")
        elif any(kw in details_lower for kw in ["disease", "condition", "diagnosis", "syndrome"]) or \
             any(kw in detected_lower for kw in ["disease", "syndrome", "disorder", "condition"]):
            boost += _BOOST_FAKE_DISEASE
            reasons.append(f"Fake/unverified disease detected: '{h.detected_text}' (+{_BOOST_FAKE_DISEASE})")
        else:
            boost += _BOOST_GENERIC
            reasons.append(f"Hallucinated claim: '{h.detected_text}' (+{_BOOST_GENERIC})")

    return boost, reasons


# ---------------------------------------------------------------------------
# Issue 2 — Educational content detection
# ---------------------------------------------------------------------------

# Emergency symptom keywords — presence means content is NOT purely educational
_EMERGENCY_SYMPTOM_KW = [
    "chest pain", "heart attack", "stroke", "unconscious", "unresponsive",
    "breathing difficulty", "shortness of breath", "dyspnea", "cardiac arrest",
    "seizure", "anaphylaxis", "hemorrhage", "severe bleeding", "overdose",
]

# Dangerous advice keywords — presence means content is NOT purely educational
_DANGEROUS_ADVICE_KW = [
    "treat at home", "treated at home", "stay home", "stay at home",
    "rest at home", "wait a few days", "wait two days", "wait 2 days",
    "ignore symptoms", "no need to see a doctor", "don't see a doctor",
    "do nothing", "symptoms are not serious", "not serious",
]


def _is_educational_only(
    text: str,
    hallucinations: list,
    invalid_claims: list,
) -> bool:
    """
    Return True when the content is safe educational information with no
    hallucinations, no invalid claims, no emergency symptoms, and no
    dangerous advice — warranting a forced LOW classification.
    """
    # Condition 1: zero active hallucinations
    if any(h.is_hallucination for h in hallucinations):
        return False

    # Condition 2: zero invalid claims
    if any(not v.is_valid for v in invalid_claims):
        return False

    normalised = text.lower()

    # Condition 3: no emergency symptoms present
    if any(kw in normalised for kw in _EMERGENCY_SYMPTOM_KW):
        return False

    # Condition 4: no dangerous advice present
    if any(kw in normalised for kw in _DANGEROUS_ADVICE_KW):
        return False

    return True


class RiskAgent(BaseAgent):
    """
    Phase 4 — Risk Intelligence Engine.

    Replaces the naive hallucination-count heuristic with a multi-dimensional
    weighted formula that considers symptom severity, urgency, and patient
    vulnerability, then applies hallucination boosts.
    """

    def __init__(self) -> None:
        self._severity_calc = SeverityCalculator()
        self._urgency_calc = UrgencyCalculator()
        self._vulnerability_calc = VulnerabilityCalculator()

    @property
    def agent_name(self) -> str:
        return "RiskAgent"

    def process(self, context: PipelineContext) -> PipelineContext:
        start_time = time.perf_counter()
        logger.info("[RiskAgent] started")

        try:
            # Combine query + AI response for symptom analysis
            combined_text = f"{context.query} {context.ai_response}"
            dangerous_keywords = [
                "drink bleach",
                "consume bleach",
                "bleach mixed",
                "drink disinfectant",
                "kerosene",
                "gasoline",
                "turpentine",
                "stop insulin",
                "skip chemotherapy",
                "stop all medications",
                "avoid seeing a doctor",
                "never see a doctor",
                "cures cancer",
                "miracle cure",
                "100% cure",
                "guaranteed cure",
            ]

            dangerous_advice_detected = any(
                kw in combined_text.lower()
                for kw in dangerous_keywords
            )
            # ----------------------------------------------------------------
            # Issue 2 — Educational content shortcut
            # Pure factual statements (e.g. "Diabetes is a chronic metabolic
            # disease") must not generate MODERATE/HIGH/CRITICAL risk.
            # ----------------------------------------------------------------
            if _is_educational_only(
                text=combined_text,
                hallucinations=context.hallucinations,
                invalid_claims=context.validations,
            ):
                context.risk_score = 0.10
                context.risk_level = "LOW"

                breakdown = RiskBreakdown(
                    severity_score=0.30,
                    urgency_score=0.30,
                    vulnerability_score=0.50,
                    hallucination_boost=0.0,
                    raw_score=0.10,
                    final_score=0.10,
                    risk_level="LOW",
                )
                context.risk_breakdown = breakdown

                assessment = RiskAssessment(
                    risk_level="LOW",
                    risk_score=0.10,
                    reasoning=(
                        "Educational content shortcut applied: no emergency symptoms, "
                        "no hallucinations, no invalid claims, no dangerous advice detected. "
                        "Content classified as safe educational information."
                    ),
                    breakdown=breakdown,
                )
                context.metadata["risk_assessment"] = assessment.model_dump()
                logger.info(
                    "[RiskAgent] educational content shortcut applied — risk_level=LOW risk_score=0.10"
                )
                status = "SUCCESS"

                elapsed = (time.perf_counter() - start_time) * 1000
                logger.info(f"[RiskAgent] completed time={elapsed:.2f}ms status={status}")

                trace = AgentTrace(
                    agent_name=self.agent_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    execution_time_ms=elapsed,
                    status=status,
                )
                context.traces.append(trace)
                return context

            severity = self._severity_calc.calculate(combined_text)
            urgency = self._urgency_calc.calculate(combined_text)
            vulnerability = self._vulnerability_calc.calculate(
                age=context.patient_age,
                comorbidities=context.comorbidities,
            )

            # ----------------------------------------------------------------
            # 2. Weighted formula
            # ----------------------------------------------------------------
            raw_score = (severity * 0.4) + (urgency * 0.3) + (vulnerability * 0.3)

            # ----------------------------------------------------------------
            # 3. Hallucination boosts
            # ----------------------------------------------------------------
            hal_boost, boost_reasons = _compute_hallucination_boost(context.hallucinations)
            final_score = min(raw_score + hal_boost, 1.0)
            # Keep API scores aligned with legacy expectations.
            if final_score > 0.95:
                final_score = 0.95

            # ----------------------------------------------------------------
            # 4. Map to risk level
            # ----------------------------------------------------------------
            risk_level = _resolve_risk_level(final_score)

            if dangerous_advice_detected:
                final_score = max(final_score, 0.90)
                risk_level = "CRITICAL"

            # ----------------------------------------------------------------
            # 5. Build reasoning string
            # ----------------------------------------------------------------
            reasoning_parts = [
                f"Severity={severity:.3f} (×0.4 → {severity * 0.4:.3f})",
                f"Urgency={urgency:.3f} (×0.3 → {urgency * 0.3:.3f})",
                f"Vulnerability={vulnerability:.3f} (×0.3 → {vulnerability * 0.3:.3f})",
                f"Raw score={raw_score:.3f}",
            ]

            if dangerous_advice_detected:
                reasoning_parts.append(
                    "Dangerous medical advice detected. Risk automatically escalated to CRITICAL."
                )
            if boost_reasons:
                reasoning_parts.append(f"Hallucination boosts: {'; '.join(boost_reasons)}")
            reasoning_parts.append(f"Final score={final_score:.3f} → {risk_level}")
            reasoning = ". ".join(reasoning_parts)

            # ----------------------------------------------------------------
            # 6. Populate context
            # ----------------------------------------------------------------
            context.risk_score = round(final_score, 4)
            context.risk_level = risk_level

            breakdown = RiskBreakdown(
                severity_score=round(severity, 4),
                urgency_score=round(urgency, 4),
                vulnerability_score=round(vulnerability, 4),
                hallucination_boost=round(hal_boost, 4),
                raw_score=round(raw_score, 4),
                final_score=round(final_score, 4),
                risk_level=risk_level,
            )
            context.risk_breakdown = breakdown

            assessment = RiskAssessment(
                risk_level=risk_level,
                risk_score=round(final_score, 4),
                reasoning=reasoning,
                breakdown=breakdown,
            )
            context.metadata["risk_assessment"] = assessment.model_dump()

            logger.info(
                f"[RiskAgent] severity={severity:.3f} urgency={urgency:.3f} "
                f"vulnerability={vulnerability:.3f} boost={hal_boost:.3f} "
                f"final={final_score:.3f} level={risk_level}"
            )
            status = "SUCCESS"

        except Exception as exc:
            logger.error(f"[RiskAgent] error: {exc}", exc_info=True)
            context.risk_level = "MODERATE"
            context.risk_score = 0.50
            context.metadata["risk_agent_error"] = str(exc)
            status = "FAILED"

        # --------------------------------------------------------------------
        # A2A message to GeneratorAgent
        # --------------------------------------------------------------------
        msg = AgentMessage(
            sender=self.agent_name,
            receiver="GeneratorAgent",
            payload=(
                f"Risk assessment finalised. "
                f"Level: {context.risk_level}, Score: {context.risk_score}. "
                f"Breakdown: severity={context.risk_breakdown.severity_score if context.risk_breakdown else 'N/A'}, "
                f"urgency={context.risk_breakdown.urgency_score if context.risk_breakdown else 'N/A'}, "
                f"vulnerability={context.risk_breakdown.vulnerability_score if context.risk_breakdown else 'N/A'}"
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        context.metadata.setdefault("message_history", []).append(msg.model_dump())

        # --------------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------------
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"[RiskAgent] completed time={elapsed:.2f}ms status={status}")

        trace = AgentTrace(
            agent_name=self.agent_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=elapsed,
            status=status,
        )
        context.traces.append(trace)
        return context
