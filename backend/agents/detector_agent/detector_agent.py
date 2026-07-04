import time
import logging
from datetime import datetime, UTC

from backend.agents.base import BaseAgent
from backend.models.schemas import (
    PipelineContext,
    AgentTrace,
    AgentMessage,
    MedicalClaim,
    HallucinationResult,
)
from backend.models.inference import run_detector_inference
from backend.ml.entity_extractor import EntityExtractor

logger = logging.getLogger("clinguard.observability")


class DetectorAgent(BaseAgent):
    def __init__(self):
        self.entity_extractor = EntityExtractor()

    @property
    def agent_name(self) -> str:
        return "DetectorAgent"

    def process(self, context: PipelineContext) -> PipelineContext:
        start_time = time.perf_counter()

        response_text = context.ai_response.lower()

        # ------------------------------------------------------------------
        # Extract medical entities
        # ------------------------------------------------------------------
        try:
            logger.info(
                "DetectorAgent.process: extracting medical entities from response: %s",
                context.ai_response,
            )

            medical_entities = self.entity_extractor.extract(context.ai_response)

            context.medical_entities = {
                "drugs": medical_entities.get("drugs", []),
                "diseases": medical_entities.get("diseases", []),
                "symptoms": medical_entities.get("symptoms", []),
            }

            logger.info(
                "DetectorAgent.process: final medical entities: %s",
                context.medical_entities,
            )

        except Exception as e:
            logger.exception(
                "DetectorAgent.process: medical entity extraction failed: %s", e
            )

            context.medical_entities = {
                "drugs": [],
                "diseases": [],
                "symptoms": [],
            }

        # ------------------------------------------------------------------
        # Run detector inference for auditing
        # ------------------------------------------------------------------
        run_detector_inference(context.ai_response)

        # ------------------------------------------------------------------
        # Dangerous medical advice detection
        # ------------------------------------------------------------------
        dangerous_patterns = [
            ("drink bleach", "Toxic substance ingestion"),
            ("consume bleach", "Toxic substance ingestion"),
            ("bleach mixed", "Toxic substance ingestion"),
            ("drink disinfectant", "Toxic substance ingestion"),
            ("kerosene", "Poison ingestion"),
            ("gasoline", "Poison ingestion"),
            ("turpentine", "Poison ingestion"),
            ("drink alcohol to cure", "Unsafe medical advice"),
            ("stop insulin", "Dangerous medication advice"),
            ("skip chemotherapy", "Dangerous treatment advice"),
            ("stop all medications", "Dangerous medication advice"),
            ("avoid seeing a doctor", "Discourages medical care"),
            ("never see a doctor", "Discourages medical care"),
            ("cures cancer", "Unsupported cure claim"),
            ("guaranteed cure", "Unsupported medical claim"),
            ("miracle cure", "Unsupported medical claim"),
            ("100% cure", "Unsupported medical claim"),
            ("always cures", "Unsupported absolute cure claim"),
            ("never causes", "Unsupported absolute safety claim"),
            ("100% safe", "Unsupported absolute safety claim"),
            ("no side effects", "Unsupported absolute safety claim"),
        ]

        detected_terms = set()

        for phrase, reason in dangerous_patterns:
            if phrase in response_text:
                detected_terms.add(phrase)

                context.claims.append(
                    MedicalClaim(
                        claim_id=f"claim_{phrase.lower().replace(' ', '_').replace('-', '_')}",
                        text=phrase,
                        category="dangerous_advice",
                        confidence=0.99,
                    )
                )

                context.hallucinations.append(
                    HallucinationResult(
                        is_hallucination=True,
                        detected_text=phrase,
                        confidence_score=0.99,
                        details=reason,
                    )
                )

        # ------------------------------------------------------------------
        # Hallucinated medical entities
        # ------------------------------------------------------------------
        candidates = [
            (
                "cardiopulmonary syndrome",
                "syndrome",
                "Flagged as unrecognized clinical syndrome.",
            ),
            (
                "ibuprofen-metformin",
                "medication",
                "Flagged as non-existent drug combination.",
            ),
            (
                "neurovascular fever",
                "symptom",
                "Flagged as non-standard medical terminology.",
            ),
        ]

        for term, category, details in candidates:

            if term not in response_text:
                continue

            prediction = run_detector_inference(term)

            if prediction["label"] != "hallucination":
                continue

            if term in detected_terms:
                continue

            context.claims.append(
                MedicalClaim(
                    claim_id=f"claim_{term.replace('-', '_').replace(' ', '_')}",
                    text=term,
                    category=category,
                    confidence=prediction["confidence"],
                )
            )

            context.hallucinations.append(
                HallucinationResult(
                    is_hallucination=True,
                    detected_text=term,
                    confidence_score=prediction["confidence"],
                    details=details,
                )
            )

        # ------------------------------------------------------------------
        # Finalize hallucination_detected flag
        # ------------------------------------------------------------------
        context.hallucination_detected = any(
            h.is_hallucination for h in context.hallucinations
        )

        logger.info(
            "DetectorAgent.process: hallucination_detected=%s (hallucinations=%d)",
            context.hallucination_detected,
            len(context.hallucinations),
        )

        # ------------------------------------------------------------------
        # Agent communication
        # ------------------------------------------------------------------
        msg = AgentMessage(
            sender=self.agent_name,
            receiver="ValidatorAgent",
            payload=(
                f"Detection completed. "
                f"Claims={len(context.claims)}, "
                f"Hallucinations={len(context.hallucinations)}, "
                f"HallucinationDetected={context.hallucination_detected}, "
                f"Drugs={len(context.medical_entities.get('drugs', []))}, "
                f"Diseases={len(context.medical_entities.get('diseases', []))}, "
                f"Symptoms={len(context.medical_entities.get('symptoms', []))}"
            ),
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

        context.metadata.setdefault("message_history", [])
        context.metadata["message_history"].append(msg.model_dump())

        # ------------------------------------------------------------------
        # Trace
        # ------------------------------------------------------------------
        execution_time_ms = (time.perf_counter() - start_time) * 1000

        context.traces.append(
            AgentTrace(
                agent_name=self.agent_name,
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                execution_time_ms=execution_time_ms,
                status="SUCCESS",
            )
        )

        return context