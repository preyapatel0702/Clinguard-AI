class MedicalEvidenceChecker:
    KNOWN_VALID_TERMS = {
        "diabetes",
        "hypertension",
        "asthma",
        "myocardial infarction",
        "pneumonia",
        "aspirin",
        "metformin",
        "ibuprofen",
        "insulin",
        "amoxicillin"
    }

    def search(self, term: str) -> dict:
        """
        Searches mock medical evidence for a given term.
        """
        is_known = term.lower() in self.KNOWN_VALID_TERMS
        evidence_count = 10 if is_known else 0
        return {
            "evidence_found": is_known,
            "evidence_count": evidence_count
        }
