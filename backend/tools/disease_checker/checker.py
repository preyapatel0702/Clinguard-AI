class DiseaseChecker:
    VALID_DISEASES = {
        "diabetes",
        "hypertension",
        "asthma",
        "myocardial infarction",
        "pneumonia"
    }

    def validate_disease(self, name: str) -> dict:
        """
        Validates if a disease name exists in the mock database.
        """
        exists = name.lower() in self.VALID_DISEASES
        return {
            "exists": exists,
            "source": "Clinical disease database (mock)",
            "confidence": 0.95 if exists else 0.0
        }
