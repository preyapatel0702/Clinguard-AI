import logging
import re

from backend.models.schemas import ClaimExplanation, PipelineContext, ValidationResult


logger = logging.getLogger("clinguard.observability")


class ExplanationEngine:
    def generate(self, context: PipelineContext) -> list[ClaimExplanation]:
        logger.info("phase9.explanation_generation started patient_id=%s", context.patient_id)
        explanations = [
            self._explain_validation(validation, context)
            for validation in context.validations
        ]
        logger.info("phase9.explanation_generation completed count=%s", len(explanations))
        return explanations

    def _explain_validation(
        self,
        validation: ValidationResult,
        context: PipelineContext,
    ) -> ClaimExplanation:
        claim_text = validation.claim_text or validation.claim_id
        related_entities = self._related_entities(claim_text, context.medical_entities)
        status = "SUPPORTED" if validation.is_valid else "UNSUPPORTED"

        return ClaimExplanation(
            claim_id=validation.claim_id,
            claim_text=claim_text,
            validation_status=status,
            confidence_score=validation.confidence,
            evidence_source=validation.source,
            reasoning=validation.reasoning,
            related_entities=related_entities,
        )

    def _related_entities(
        self,
        claim_text: str,
        medical_entities: dict[str, list[dict]],
    ) -> list[str]:
        normalized_claim = claim_text.lower()
        related: list[str] = []

        for category in ("drugs", "diseases", "symptoms"):
            for entity in medical_entities.get(category, []):
                text = str(entity.get("text", "")).strip().lower()
                if text and re.search(rf"\b{re.escape(text)}\b", normalized_claim):
                    if text not in related:
                        related.append(text)

        return related
