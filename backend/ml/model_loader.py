import os
import logging

logger = logging.getLogger(__name__)

medical_ner = None

USE_TRANSFORMERS = os.getenv("USE_TRANSFORMERS", "false").lower() == "true"

if USE_TRANSFORMERS:
    try:
        from transformers import pipeline

        medical_ner = pipeline(
            "ner",
            model="d4data/biomedical-ner-all",
            aggregation_strategy="simple",
        )

        logger.info("Biomedical NER model loaded successfully.")

    except Exception as e:
        logger.warning(f"Could not load biomedical NER model: {e}")
        medical_ner = None
else:
    logger.info("Transformer model disabled.")
