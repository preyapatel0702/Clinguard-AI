"""
evaluator_agent.py
------------------
Phase 6 — Agent Self-Evaluation

Evaluates the final pipeline output across four dimensions:

1. Hallucination Coverage  (0–100)
   Were all detected hallucinations addressed in the safe response?

2. Validation Consistency  (0–100)
   Are invalid claims reflected in the safe response?

3. Risk Consistency        (0–100)
   Does the response tone / content match the declared risk level?

4. Safety Completeness     (0–100)
   Does the safe response contain safety guidance and disclaimer?

Overall score = weighted average (25% each dimension).
PASS threshold = 80.
If FAIL, a warning is appended to context.safe_response.
"""


import time
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from backend.agents.base import BaseAgent
from backend.models.schemas import (
    PipelineContext,
    AgentTrace,
    AgentMessage,
    EvaluationReport,
)

logger = logging.getLogger("clinguard.observability")

# ---------------------------------------------------------------------------
# Safety keyword sets used in safety completeness check
# ---------------------------------------------------------------------------
_SAFETY_KEYWORDS = [
    "consult", "healthcare professional", "physician", "doctor",
    "emergency", "seek medical", "call emergency", "disclaimer",
    "important", "do not", "licensed", "professional advice",
    "medical evaluation", "seek immediate",
]

_EMERGENCY_KEYWORDS = [
    "emergency services", "call 911", "call 112", "call 999",
    "seek immediate", "medical emergency", "life-threatening",
]

# Risk levels that require an emergency statement
_HIGH_RISK_LEVELS = {"HIGH", "CRITICAL"}

# Hallucination-related phrases expected in the safe response
_HALLUCINATION_PHRASES = [
    "potentially unsafe",
    "hallucination",
    "unverified",
    "consult a licensed",
    "do not start",
    "do not stop",
    "do not modify",
    "medication",
    "removed",
    "unsafe",
    "could not be verified",
]

_DANGEROUS_PATTERNS = [
    "drink bleach",
    "consume bleach",
    "bleach mixed",
    "drink disinfectant",
    "kerosene",
    "gasoline",
    "turpentine",
    "stop insulin",
    "skip chemotherapy",
    "avoid seeing a doctor",
    "cures cancer",
    "guaranteed cure",
]

# Pass threshold
_PASS_THRESHOLD = 80.0

_FAIL_WARNING = (
    "\n\n🔴 EVALUATION WARNING: This response did not fully meet quality and safety standards. "
    "Please treat all information with caution and consult a qualified healthcare professional "
    "before acting on any advice above."
)


class EvaluatorAgent(BaseAgent):
    """
    Phase 6 — Self-evaluation agent that scores the pipeline output 0–100
    and determines PASS / FAIL.
    """

    @property
    def agent_name(self) -> str:
        return "EvaluatorAgent"

    def process(self, context: PipelineContext) -> PipelineContext:
        start_time = time.perf_counter()
        logger.info("[EvaluatorAgent] started")

        safe_response_lower = (context.safe_response or "").lower()
        failure_reasons: list[str] = []
        status = "SUCCESS"

        try:
            # ----------------------------------------------------------------
            # Dimension 1: Hallucination Coverage
            # ----------------------------------------------------------------
            coverage_score = self._score_hallucination_coverage(
                hallucinations=context.hallucinations,
                safe_response_lower=safe_response_lower,
                failure_reasons=failure_reasons,
            )
            logger.info(f"[EvaluatorAgent] coverage_score={coverage_score:.1f}")

            # ----------------------------------------------------------------
            # Dimension 2: Validation Consistency
            # ----------------------------------------------------------------
            consistency_score = self._score_validation_consistency(
                validations=context.validations,
                safe_response_lower=safe_response_lower,
                failure_reasons=failure_reasons,
            )
            logger.info(f"[EvaluatorAgent] consistency_score={consistency_score:.1f}")

            # ----------------------------------------------------------------
            # Dimension 3: Risk Consistency
            # ----------------------------------------------------------------
            risk_consistency_score = self._score_risk_consistency(
                risk_level=context.risk_level,
                safe_response_lower=safe_response_lower,
                failure_reasons=failure_reasons,
            )
            logger.info(f"[EvaluatorAgent] risk_consistency_score={risk_consistency_score:.1f}")

            # ----------------------------------------------------------------
            # Dimension 4: Safety Completeness
            # ----------------------------------------------------------------
            safety_score = self._score_safety_completeness(
                safe_response_lower=safe_response_lower,
                failure_reasons=failure_reasons,
            )
            logger.info(f"[EvaluatorAgent] safety_score={safety_score:.1f}")

            # ------------------------------------------------------------
            # Final safety gate: dangerous advice must never remain
            # ------------------------------------------------------------
            if self._contains_dangerous_advice(safe_response_lower):
                safety_score = 0
                coverage_score = min(coverage_score, 30)

                failure_reasons.append(
                    "Dangerous medical advice still present in final response."
                )

            # ----------------------------------------------------------------
            # Overall score (equal weights)
            # ----------------------------------------------------------------
            overall_score = (
                coverage_score * 0.25
                + consistency_score * 0.25
                + risk_consistency_score * 0.25
                + safety_score * 0.25
            )
            passed = overall_score >= _PASS_THRESHOLD

            # ----------------------------------------------------------------
            # Append warning to safe_response on FAIL
            # ----------------------------------------------------------------
            if not passed:
                context.safe_response = (context.safe_response or "") + _FAIL_WARNING
                failure_reasons.append(
                    f"Overall score {overall_score:.1f} below pass threshold {_PASS_THRESHOLD}"
                )
                logger.warning(
                    f"[EvaluatorAgent] FAIL — overall_score={overall_score:.1f} "
                    f"reasons: {failure_reasons}"
                )
            else:
                logger.info(
                    f"[EvaluatorAgent] PASS — overall_score={overall_score:.1f}"
                )

            # ----------------------------------------------------------------
            # Store EvaluationReport in context
            # ----------------------------------------------------------------
            report = EvaluationReport(
                coverage_score=round(coverage_score, 2),
                consistency_score=round(consistency_score, 2),
                risk_consistency_score=round(risk_consistency_score, 2),
                safety_score=round(safety_score, 2),
                overall_score=round(overall_score, 2),
                passed=passed,
                failure_reasons=failure_reasons,
            )
            context.evaluation_report = report
            context.metadata["evaluation_report"] = report.model_dump()
            context.metadata["evaluation_passed"] = passed

        except Exception as exc:
            logger.error(f"[EvaluatorAgent] error: {exc}", exc_info=True)

            report = EvaluationReport(
                coverage_score=0,
                consistency_score=0,
                risk_consistency_score=0,
                safety_score=0,
                overall_score=0,
                passed=False,
                failure_reasons=[str(exc)],
            )

            context.evaluation_report = report
            context.metadata["evaluation_report"] = report.model_dump()
            context.metadata["evaluation_passed"] = False
            context.metadata["evaluator_error"] = str(exc)

            status = "FAILED"

        # --------------------------------------------------------------------
        # A2A message to MemoryAgent
        # --------------------------------------------------------------------
        passed_flag = context.metadata.get("evaluation_passed", False)
        msg = AgentMessage(
            sender=self.agent_name,
            receiver="MemoryAgent",
            payload=f"Evaluation completed. Passed: {passed_flag}. Overall: {context.evaluation_report.overall_score if context.evaluation_report else 'N/A'}.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        context.metadata.setdefault("message_history", []).append(msg.model_dump())

        # --------------------------------------------------------------------
        # Trace
        # --------------------------------------------------------------------
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"[EvaluatorAgent] completed time={elapsed:.2f}ms status={status}")

        trace = AgentTrace(
            agent_name=self.agent_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=elapsed,
            status=status,
        )
        context.traces.append(trace)
        return context
    
    def _contains_dangerous_advice(self, text: str) -> bool:
        safe_context = [
            "do not",
            "avoid",
            "never",
            "unsafe",
            "removed",
            "not recommended",
            "warning",
        ]

        for pattern in _DANGEROUS_PATTERNS:
            idx = text.find(pattern)

            if idx == -1:
                continue

            window = text[max(0, idx - 40):idx]

            if any(keyword in window for keyword in safe_context):
                continue

            return True

        return False

    # -------------------------------------------------------------------------
    # Scoring helpers
    # -------------------------------------------------------------------------

    def _score_hallucination_coverage(
        self,
        hallucinations: list,
        safe_response_lower: str,
        failure_reasons: list[str],
    ) -> float:
        """
        Score how well the safe response addresses detected hallucinations.
        100 if no hallucinations exist or all are acknowledged.
        Penalised per uncovered hallucination.
        """
        active = [h for h in hallucinations if h.is_hallucination]
        if not active:
            return 100.0

        # Check if any hallucination-acknowledgement phrases are present
        covered = True

        for h in active:
            if h.detected_text.lower() in safe_response_lower:
                covered = False
                break

        covered = covered and any(
            phrase in safe_response_lower
            for phrase in _HALLUCINATION_PHRASES
        )
        if covered:
            return 100.0

        failure_reasons.append(
            f"Hallucination coverage: {len(active)} hallucination(s) detected but "
            "safe_response does not acknowledge them adequately"
        )
        # Deduct 20 points per uncovered hallucination (min 0)
        score = max(0.0, 100.0 - (len(active) * 20.0))
        return score

    def _score_validation_consistency(
        self,
        validations,
        safe_response_lower: str,
        failure_reasons: list[str],
    ) -> float:
        """
        Measures whether invalid medical claims are properly reflected
        in the generated safe response.

        Scoring:
        - Starts at 100.
        - If invalid claims exist, the response should acknowledge that
        some information was unsafe, removed, or could not be verified.
        - Missing acknowledgement is penalized.
        """

        score = 100.0

        safe_response_lower = (safe_response_lower or "").lower()

        # Collect invalid claims safely
        invalid_claims = [
            claim
            for claim in validations
            if not getattr(claim, "is_valid", True)
        ]

        # Nothing to validate
        if not invalid_claims:
            return score

        # Check whether the response acknowledges invalid claims
        acknowledged = any(
            phrase in safe_response_lower
            for phrase in [
                "could not be verified",
                "not verified",
                "unverified",
                "unsafe",
                "potentially unsafe",
                "removed",
                "blocked",
                "incorrect",
                "inaccurate",
                "medical advice was detected",
            ]
        )

        if not acknowledged:
            penalty = min(60.0, len(invalid_claims) * 30.0)
            score -= penalty

            failure_reasons.append(
                "Invalid medical claims are not reflected in the safe response."
            )

        return max(score, 0.0)
    


    def _score_risk_consistency(
        self,
        risk_level: str,
        safe_response_lower: str,
        failure_reasons: list[str],
    ) -> float:
        """
        Checks whether the generated safe response matches the declared
        clinical risk level.
        """

        score = 100.0

        safe_response_lower = (safe_response_lower or "").lower()

        if risk_level in {"HIGH", "CRITICAL"}:

            if not any(
                keyword in safe_response_lower
                for keyword in [
                    "emergency",
                    "seek immediate",
                    "consult",
                    "healthcare professional",
                    "licensed",
                ]
            ):
                score -= 50
                failure_reasons.append(
                    "High-risk response missing emergency guidance."
                )

        elif risk_level == "MODERATE":

            if "consult" not in safe_response_lower:
                score -= 20

        return max(score, 0.0)

    def _score_safety_completeness(
        self,
        safe_response_lower: str,
        failure_reasons: list[str],
    ) -> float:
        """
        Score the presence of safety guidance elements.
        Checks for: disclaimer, consultation advice, emergency guidance.
        """
        score = 0.0
        max_score = 100.0

        # Disclaimer presence (40 points)
        has_disclaimer = any(
            kw in safe_response_lower
            for kw in ["disclaimer", "ai-generated", "always consult", "do not"]
        )
        if has_disclaimer:
            score += 40.0
        else:
            failure_reasons.append("Safety completeness: mandatory disclaimer not found in response")

        # Consultation advice (35 points)
        has_consultation = any(
            kw in safe_response_lower
            for kw in ["consult", "healthcare professional", "physician", "doctor", "licensed"]
        )
        if has_consultation:
            score += 35.0
        else:
            failure_reasons.append(
                "Safety completeness: no consultation advice found in response"
            )

        # Medication warning (25 points — important for pharmaceutical hallucinations)
        has_med_warning = any(
            kw in safe_response_lower
            for kw in [
                "do not start", "do not stop", "do not modify", "medication",
                "prescription", "pharmacist", "drug", "dosage",
            ]
        )
        if has_med_warning:
            score += 25.0
        else:
            # Partial credit — not all responses mention medications
            score += 15.0

        return min(score, max_score)
