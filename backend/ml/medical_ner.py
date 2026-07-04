from backend.ml.model_loader import medical_ner
import logging


logger = logging.getLogger("clinguard.observability")


class MedicalNER:
    def extract_entities(self, text: str):
        results = medical_ner(text)

        logger.info("MedicalNER.extract_entities: raw HuggingFace NER output: %s", results)
        print("MedicalNER RAW HF OUTPUT:", results)

        entities = []

        for item in results:

            word = item["word"]
            label = item.get("entity_group") or item.get("entity") or "UNKNOWN"

            if word.startswith("##") and entities:
                entities[-1]["text"] += word.replace("##", "")
                logger.info("MedicalNER.extract_entities: merged wordpiece into entity: %s", entities[-1])
                print("MedicalNER EXTRACTED ENTITY:", entities[-1])
                continue

            entity = {
                "text": word.strip(),
                "label": label,
                "score": float(round(float(item["score"]), 3)),
            }
            entities.append(entity)
            logger.info("MedicalNER.extract_entities: extracted entity: %s", entity)
            print("MedicalNER EXTRACTED ENTITY:", entity)

        logger.info("MedicalNER.extract_entities: final extracted entities: %s", entities)
        print("MedicalNER FINAL ENTITIES:", entities)
        return entities
