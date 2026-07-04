from multiprocessing import context
import time
import logging
from datetime import datetime,UTC
from backend.agents.base import BaseAgent
from backend.models.schemas import PipelineContext, AgentTrace, AgentMessage, ValidationResult
from backend.tools.disease_checker import DiseaseChecker
from backend.tools.drug_checker import DrugChecker
from backend.tools.medical_evidence import MedicalEvidenceChecker
from backend.knowledge.validator_service import MedicalValidator

DANGEROUS_MEDICAL_CLAIMS = {
    "drink bleach": "Bleach is poisonous and should never be ingested.",
    "consume bleach": "Bleach is poisonous and should never be ingested.",
    "bleach mixed": "Bleach ingestion is medically dangerous.",
    "drink disinfectant": "Disinfectants are toxic to humans.",
    "kerosene": "Kerosene ingestion is dangerous.",
    "gasoline": "Gasoline ingestion is dangerous.",
    "turpentine": "Turpentine ingestion is dangerous.",
    "stop insulin": "Stopping insulin abruptly can be life-threatening.",
    "skip chemotherapy": "Stopping chemotherapy without oncologist guidance is dangerous.",
    "stop all medications": "Stopping prescribed medication without medical supervision is unsafe.",
    "avoid seeing a doctor": "Discouraging medical evaluation is unsafe.",
    "don't see a doctor": "Discouraging medical evaluation is unsafe.",
    "never see a doctor": "Discouraging medical evaluation is unsafe.",
    "miracle cure": "Unsupported medical cure claim.",
    "guaranteed cure": "Unsupported medical cure claim.",
    "100% cure": "Unsupported medical cure claim.",
    "always cures": "Unsupported absolute cure claim.",
    "never causes": "Unsupported absolute safety claim.",
    "100% safe": "Unsupported absolute safety claim.",
    "no side effects": "Unsupported absolute safety claim.",
}

class ValidatorAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "ValidatorAgent"

    def process(self, context: PipelineContext) -> PipelineContext:
        start_time = time.perf_counter()
        
        # Setup standard logger
        logger = logging.getLogger("clinguard.observability")
        logger.info("ValidatorAgent: validation started")

        disease_checker = DiseaseChecker()
        drug_checker = DrugChecker()
        evidence_checker = MedicalEvidenceChecker()

        # Clear existing validations to prevent duplicates if run multiple times
        context.validations = []

        for claim in context.claims:
            term = claim.text
            
            # Run modular validation tools
            logger.info("ValidatorAgent: tool used: DiseaseChecker")
            disease_res = disease_checker.validate_disease(term)
            
            logger.info("ValidatorAgent: tool used: DrugChecker")
            drug_res = drug_checker.validate_drug(term)
            
            logger.info("ValidatorAgent: tool used: MedicalEvidenceChecker")
            evidence_res = evidence_checker.search(term)
            
            # Combine results
            disease_exists = disease_res["exists"]
            drug_exists = drug_res["exists"]
            evidence_found = evidence_res["evidence_found"]
            
            is_valid = disease_exists or drug_exists or evidence_found
            
            if disease_exists:
                source = disease_res["source"]
                confidence = disease_res["confidence"]
                reasoning = "Disease record found in database with supporting medical evidence."
            elif drug_exists:
                source = drug_res["source"]
                confidence = drug_res["confidence"]
                reasoning = "Drug record found in database with supporting medical evidence."
            elif evidence_found:
                source = "ClinGuard Medical Knowledge Base"
                confidence = 0.85
                reasoning = "Supporting medical evidence located."
            else:
                source = "ClinGuard Clinical Validation Engine"
                confidence = 0.99
                reasoning = (
                    "No disease record found and no supporting medical evidence located."
                )

            result = ValidationResult(
                claim_id=claim.claim_id,
                claim_text=claim.text,
                is_valid=is_valid,
                source=source,
                confidence=confidence,
                reasoning=reasoning
            )
            context.validations.append(result)

        logger.info("ValidatorAgent: validation completed")

        # Preserve hallucination flag from DetectorAgent.
        # If DetectorAgent already detected one, keep it.
        # Otherwise derive it from the hallucinations list.
        context.hallucination_detected = (
            context.hallucination_detected
            or any(h.is_hallucination for h in context.hallucinations)
        )

        response_lower = context.ai_response.lower()

        for phrase, reason in DANGEROUS_MEDICAL_CLAIMS.items():

            if phrase in response_lower:

                # Reinforce hallucination detection
                context.hallucination_detected = True

                context.validations.append(
                    ValidationResult(
                        claim_id=f"unsafe_{phrase.replace(' ', '_')}",
                        claim_text=phrase,
                        is_valid=False,
                        source="ClinGuard Safety Rules",
                        confidence=1.0,
                        reasoning=reason,
                    )
                )

        # ==========================================
        # Phase 8B - Knowledge Base Validation
        # ==========================================

        validator = MedicalValidator()

        drugs = context.medical_entities.get("drugs", [])
        diseases = context.medical_entities.get("diseases", [])

        print("PHASE 8B")
        print("DRUGS:", drugs)
        print("DISEASES:", diseases)

        for drug in drugs:
            for disease in diseases:

                supported, confidence = validator.validate_drug_disease(
                    drug["text"],
                    disease["text"]
                )

                kb_validation = ValidationResult(
                    claim_id=f"kb_{drug['text']}_{disease['text']}",
                    claim_text=f"{drug['text']} treats {disease['text']}",
                    is_valid=supported,
                    source="Medical Knowledge Base",
                    confidence=confidence,
                    reasoning=(
                        "Drug-disease relationship supported by medical knowledge base."
                        if supported
                        else "Drug-disease relationship not found in medical knowledge base."
                    )
                )

                context.validations.append(kb_validation)



        # Simulate A2A message to RiskAgent
        msg = AgentMessage(
            sender=self.agent_name,
            receiver="RiskAgent",
            payload=f"Claims validation completed. Processed {len(context.validations)} validation results.",
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z")
        )
        if "message_history" not in context.metadata:
            context.metadata["message_history"] = []
        context.metadata["message_history"].append(msg.model_dump())

        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000

        # Create trace
        trace = AgentTrace(
            agent_name=self.agent_name,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            execution_time_ms=execution_time_ms,
            status="SUCCESS"
        )
        context.traces.append(trace)

        return context

