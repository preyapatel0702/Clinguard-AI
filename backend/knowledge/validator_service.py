from backend.knowledge.medical_kb import MEDICAL_KB

class MedicalValidator:

    def validate_drug_disease(self, drug, disease):

        drug = drug.lower()
        disease = disease.lower()

        if drug not in MEDICAL_KB:
            return False, 0.30

        supported = disease in MEDICAL_KB[drug]["treats"]

        return (
            supported,
            0.95 if supported else 0.20
        )