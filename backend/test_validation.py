import sys
import os

# Resolve backend module namespace when running inside or outside backend/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.tools.disease_checker.checker import DiseaseChecker
from backend.tools.drug_checker.checker import DrugChecker
from backend.tools.medical_evidence.checker import MedicalEvidenceChecker
from backend.agents.validator_agent.validator_agent import ValidatorAgent
from backend.models.schemas import PipelineContext, MedicalClaim

def test_disease_checker():
    checker = DiseaseChecker()
    
    # Test cardiopulmonary syndrome
    res_cps = checker.validate_disease("cardiopulmonary syndrome")
    assert res_cps["exists"] is False, "Expected cardiopulmonary syndrome to not exist in disease database"
    
    # Test diabetes
    res_dia = checker.validate_disease("diabetes")
    assert res_dia["exists"] is True, "Expected diabetes to exist in disease database"
    print("test_disease_checker: PASSED")

def test_drug_checker():
    checker = DrugChecker()
    
    # Test cardiopulmonary syndrome
    res_cps = checker.validate_drug("cardiopulmonary syndrome")
    assert res_cps["exists"] is False, "Expected cardiopulmonary syndrome to not exist in drug database"
    
    # Test aspirin
    res_asp = checker.validate_drug("aspirin")
    assert res_asp["exists"] is True, "Expected aspirin to exist in drug database"
    print("test_drug_checker: PASSED")

def test_medical_evidence_checker():
    checker = MedicalEvidenceChecker()
    
    # Test cardiopulmonary syndrome
    res_cps = checker.search("cardiopulmonary syndrome")
    assert res_cps["evidence_found"] is False, "Expected no evidence found for cardiopulmonary syndrome"
    assert res_cps["evidence_count"] == 0, "Expected evidence_count = 0 for cardiopulmonary syndrome"
    
    # Test diabetes
    res_dia = checker.search("diabetes")
    assert res_dia["evidence_found"] is True, "Expected evidence found for diabetes"
    assert res_dia["evidence_count"] > 0, "Expected evidence_count > 0 for diabetes"
    print("test_medical_evidence_checker: PASSED")

def test_validator_agent():
    agent = ValidatorAgent()
    
    # Create context with one invalid claim and one valid claim
    context = PipelineContext(
        patient_id="test_patient",
        query="Test query",
        ai_response="Diabetes and cardiopulmonary syndrome."
    )
    context.claims = [
        MedicalClaim(claim_id="claim_1", text="cardiopulmonary syndrome", category="syndrome", confidence=0.9),
        MedicalClaim(claim_id="claim_2", text="diabetes", category="disease", confidence=0.9)
    ]
    
    updated_context = agent.process(context)
    
    assert len(updated_context.validations) == 2, "Expected 2 validation results"
    
    # Check cardiopulmonary syndrome validation result
    val_cps = next(v for v in updated_context.validations if v.claim_id == "claim_1")
    assert val_cps.is_valid is False
    assert val_cps.reasoning == "No disease record found and no supporting medical evidence located."
    
    # Check diabetes validation result
    val_dia = next(v for v in updated_context.validations if v.claim_id == "claim_2")
    assert val_dia.is_valid is True
    assert "Disease record found in database with supporting medical evidence." in val_dia.reasoning
    
    print("test_validator_agent: PASSED")

if __name__ == "__main__":
    print("Running validation unit tests...")
    test_disease_checker()
    test_drug_checker()
    test_medical_evidence_checker()
    test_validator_agent()
    print("All validation tests passed successfully!")
