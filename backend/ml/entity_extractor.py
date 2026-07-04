from .medical_ner import MedicalNER
import logging
import re


logger = logging.getLogger("clinguard.observability")


COMMON_DISEASES = (
    "diabetes",
    "hypertension",
    "asthma",
    "cancer",
    "pneumonia",
    "migraine",
)


LABEL_ALIASES = {
    "drug": {
        "chemical",
        "chemicals",
        "drug",
        "drugs",
        "medication",
        "medicine",
        "pharmacologic_substance",
    },
    "disease": {
        "disease",
        "diseases",
        "disease_disorder",
        "disease_or_syndrome",
        "disorder",
        "problem",
        "diagnosis",
    },
    "symptom": {
        "symptom",
        "symptoms",
        "sign",
        "sign_symptom",
        "sign_or_symptom",
    },
}


def normalize_label(label: str) -> str:
    normalized = str(label or "").strip().lower()
    normalized = re.sub(r"^[bi]-", "", normalized)
    normalized = normalized.replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"_+", "_", normalized)
    return normalized


def normalize_text(text: str) -> str:
    return str(text or "").strip().lower()


class EntityExtractor:
    def __init__(self):
        self.ner = MedicalNER()

    def extract(self, text: str):
        entities = self.ner.extract_entities(text)

        drugs = []
        diseases = []
        symptoms = []
        seen = {
            "drug": set(),
            "disease": set(),
            "symptom": set(),
        }

        for entity in entities:
            logger.info("EntityExtractor.extract: extracted entity: %s", entity)
            print("EntityExtractor ENTITY:", entity)

            original_label = entity.get("label", "")
            normalized_label = normalize_label(original_label)
            logger.info(
                "EntityExtractor.extract: label normalization before=%r after=%r",
                original_label,
                normalized_label,
            )
            print(
                "EntityExtractor LABEL NORMALIZATION:",
                {"before": original_label, "after": normalized_label},
            )

            normalized_entity = {
                **entity,
                "text": normalize_text(entity.get("text", "")),
                "label": original_label,
            }

            if normalized_label in LABEL_ALIASES["drug"]:
                entity_key = normalized_entity["text"]
                if entity_key and entity_key not in seen["drug"]:
                    drugs.append(normalized_entity)
                    seen["drug"].add(entity_key)

            elif normalized_label in LABEL_ALIASES["disease"]:
                entity_key = normalized_entity["text"]
                if entity_key and entity_key not in seen["disease"]:
                    diseases.append(normalized_entity)
                    seen["disease"].add(entity_key)

            elif normalized_label in LABEL_ALIASES["symptom"]:
                entity_key = normalized_entity["text"]
                if entity_key and entity_key not in seen["symptom"]:
                    symptoms.append(normalized_entity)
                    seen["symptom"].add(entity_key)

        for disease in self._fallback_diseases(text):
            entity_key = disease["text"]
            if entity_key not in seen["disease"]:
                diseases.append(disease)
                seen["disease"].add(entity_key)
                logger.info("EntityExtractor.extract: fallback disease entity: %s", disease)
                print("EntityExtractor FALLBACK DISEASE:", disease)

        final_entities = {
            "drugs": drugs,
            "diseases": diseases,
            "symptoms": symptoms,
        }
        logger.info(
            "EntityExtractor.extract: final drugs=%s diseases=%s symptoms=%s",
            drugs,
            diseases,
            symptoms,
        )
        print("EntityExtractor FINAL DRUGS:", drugs)
        print("EntityExtractor FINAL DISEASES:", diseases)
        print("EntityExtractor FINAL SYMPTOMS:", symptoms)

        return final_entities

    def _fallback_diseases(self, text: str):
        matches = []

        for disease in COMMON_DISEASES:
            pattern = rf"\b{re.escape(disease)}\b"
            if re.search(pattern, text, flags=re.IGNORECASE):
                matches.append(
                    {
                        "text": disease,
                        "label": "Disease_disorder",
                        "score": 1.0,
                    }
                )

        return matches
