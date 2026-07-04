"""
explanation_engine.py
---------------------
Phase 9 — Structured Explanation Generator

Generates explanations for every major pipeline finding:
  • hallucination detections
  • validation outcomes
  • risk calculations
  • response modifications

Each explanation carries an ``explanation_id``, ``category``, ``title``,
``reasoning``, ``evidence``, ``confidence``, and ``generated_at``.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.models.audit import ClaimExplanation
from backend.models.schemas import PipelineContext

logger = logging.getLogger("clinguard.phase9.explanation")


class ExplanationEngineV2:
    """Produce rich, categorised explanations from a completed PipelineContext."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, context: PipelineContext) -> List[ClaimExplanation]:
        """Return all explanations for the given pipeline run."""
        logger.info(
            "explanation_engine.generate started patient_id=%s",
            context.patient_id,
        )
        explanations: List[ClaimExplanation] = []
        explanations.extend(self._hallucination_explanations(context))
        explanations.extend(self._validation_explanations(context))
        explanations.extend(self._risk_explanations(context))
        explanations.extend(self._response_modification_explanations(context))
        logger.info(
            "explanation_engine.generate completed count=%d",
            len(explanations),
        )
        return explanations

    # ------------------------------------------------------------------
    # Hallucination detection explanations
    # ------------------------------------------------------------------

    def _hallucination_explanations(
        self, context: PipelineContext
    ) -> List[ClaimExplanation]:
        results: List[ClaimExplanation] = []
        for hallucination in context.hallucinations:
            if not hallucination.is_hallucination:
                continue
            results.append(
                ClaimExplanation(
                    category="hallucination_detection",
                    title=f"Hallucination detected: '{hallucination.detected_text}'",
                    reasoning=hallucination.details,
                    evidence=[
                        f"Detected text: {hallucination.detected_text}",
                        f"Confidence: {hallucination.confidence_score:.2f}",
                    ],
                    confidence=hallucination.confidence_score,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Validation outcome explanations
    # ------------------------------------------------------------------

    def _validation_explanations(
        self, context: PipelineContext
    ) -> List[ClaimExplanation]:
        results: List[ClaimExplanation] = []
        for validation in context.validations:
            status = "SUPPORTED" if validation.is_valid else "UNSUPPORTED"
            claim_text = validation.claim_text or validation.claim_id
            related = self._find_related_entities(
                claim_text, context.medical_entities
            )
            evidence_items = [
                f"Claim: {claim_text}",
                f"Source: {validation.source}",
                f"Status: {status}",
            ]
            if related:
                evidence_items.append(f"Related entities: {', '.join(related)}")

            results.append(
                ClaimExplanation(
                    category="validation_outcome",
                    title=f"Claim {status}: '{claim_text}'",
                    reasoning=validation.reasoning or f"Claim was determined to be {status.lower()}.",
                    evidence=evidence_items,
                    confidence=validation.confidence,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Risk calculation explanations
    # ------------------------------------------------------------------

    def _risk_explanations(
        self, context: PipelineContext
    ) -> List[ClaimExplanation]:
        results: List[ClaimExplanation] = []
        breakdown = context.risk_breakdown
        risk_assessment: Dict[str, Any] = context.metadata.get("risk_assessment", {})

        evidence_items: List[str] = [
            f"Risk level: {context.risk_level}",
            f"Risk score: {context.risk_score:.4f}",
        ]

        reasoning_text = risk_assessment.get("reasoning", "")

        if breakdown:
            evidence_items.extend([
                f"Severity: {breakdown.severity_score:.4f}",
                f"Urgency: {breakdown.urgency_score:.4f}",
                f"Vulnerability: {breakdown.vulnerability_score:.4f}",
                f"Hallucination boost: {breakdown.hallucination_boost:.4f}",
            ])
            if not reasoning_text:
                reasoning_text = (
                    f"Risk computed as weighted combination: "
                    f"severity({breakdown.severity_score:.3f}) × 0.4 + "
                    f"urgency({breakdown.urgency_score:.3f}) × 0.3 + "
                    f"vulnerability({breakdown.vulnerability_score:.3f}) × 0.3 "
                    f"= {breakdown.raw_score:.3f}, "
                    f"boosted by {breakdown.hallucination_boost:.3f} "
                    f"to final {breakdown.final_score:.3f}."
                )

        if not reasoning_text:
            reasoning_text = f"Risk level determined as {context.risk_level} with score {context.risk_score}."

        results.append(
            ClaimExplanation(
                category="risk_calculation",
                title=f"Risk assessment: {context.risk_level} ({context.risk_score:.2f})",
                reasoning=reasoning_text,
                evidence=evidence_items,
                confidence=min(context.risk_score + 0.5, 1.0),
            )
        )
        return results

    # ------------------------------------------------------------------
    # Response modification explanations
    # ------------------------------------------------------------------

    def _response_modification_explanations(
        self, context: PipelineContext
    ) -> List[ClaimExplanation]:
        results: List[ClaimExplanation] = []
        metadata: Dict[str, Any] = context.metadata.get("safe_response_metadata", {})
        modifications: List[str] = metadata.get("modifications_made", [])
        safety_reason: str = metadata.get("safety_reason", "")

        if not modifications and not safety_reason:
            return results

        evidence_items: List[str] = []
        if modifications:
            for mod in modifications:
                evidence_items.append(f"Modification: {mod}")
        if safety_reason:
            evidence_items.append(f"Reason: {safety_reason}")

        confidence_val: float = metadata.get("confidence", 0.9)

        results.append(
            ClaimExplanation(
                category="response_modification",
                title=f"Response modified with {len(modifications)} change(s)",
                reasoning=safety_reason or "Response was modified for clinical safety.",
                evidence=evidence_items,
                confidence=confidence_val,
            )
        )
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_related_entities(
        claim_text: str,
        medical_entities: Dict[str, List[dict]],
    ) -> List[str]:
        """Find entity names that appear in the claim text."""
        normalised = claim_text.lower()
        related: List[str] = []
        for category in ("drugs", "diseases", "symptoms"):
            for entity in medical_entities.get(category, []):
                text = str(entity.get("text", "")).strip().lower()
                if text and re.search(rf"\b{re.escape(text)}\b", normalised):
                    if text not in related:
                        related.append(text)
        return related
