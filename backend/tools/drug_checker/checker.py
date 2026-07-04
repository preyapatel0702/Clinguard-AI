class DrugChecker:
    VALID_DRUGS = {
        "aspirin",
        "metformin",
        "ibuprofen",
        "insulin",
        "amoxicillin"
    }

    def validate_drug(self, name: str) -> dict:
        """
        Validates if a drug name exists in the mock database.
        """
        exists = name.lower() in self.VALID_DRUGS
        return {
            "exists": exists,
            "source": "Clinical drug database (mock)",
            "confidence": 0.95 if exists else 0.0
        }
