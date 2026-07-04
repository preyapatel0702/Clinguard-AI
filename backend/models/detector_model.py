import logging
from typing import Dict, Any

logger = logging.getLogger("clinguard.observability")

class DetectorModel:
    def __init__(self) -> None:
        self.known_hallucinations = {
            "cardiopulmonary syndrome",
            "ibuprofen-metformin",
            "neurovascular fever"
        }
        self.is_loaded = False

    def load_model(self) -> None:
        """
        Simulates model loading once.
        """
        logger.info("DetectorModel: Loading model...")
        self.is_loaded = True
        logger.info("DetectorModel: Model loaded successfully.")

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Runs prediction on input text. Checks if it contains known hallucinations.
        """
        logger.info(f"DetectorModel: Inference started for text: '{text}'")
        
        normalized_text = text.lower()
        is_hallucination = False
        
        for term in self.known_hallucinations:
            if term in normalized_text:
                is_hallucination = True
                break

        if is_hallucination:
            label = "hallucination"
            confidence = 0.95
        else:
            label = "safe"
            confidence = 0.90

        logger.info(f"DetectorModel: Inference completed. Label: {label} | Confidence: {confidence:.2f}")

        return {
            "label": label,
            "confidence": confidence
        }
