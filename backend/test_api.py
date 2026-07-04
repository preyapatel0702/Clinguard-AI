import sys
import os
from fastapi.testclient import TestClient

# Resolve backend module namespace when running inside or outside backend/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app

client = TestClient(app)

def test_health():
    """
    Test the GET /health endpoint.
    """
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ClinGuard AI"
    assert data["version"] == "0.3.0"
    print("test_health: PASSED")

def test_analyze_low_risk():
    """
    Test POST /analyze with safe medical query and response.
    """
    payload = {
        "patient_id": "123",
        "query": "What should I do for a mild headache?",
        "ai_response": "Rest in a quiet room and drink plenty of water."
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    # Assert LOW risk details
    assert data["version"] == "0.3.0"
    assert data["risk_level"] == "LOW"
    assert data["risk_score"] == 0.10
    assert len(data["hallucinations"]) == 0
    assert len(data["validated_claims"]) == 0
    assert payload["ai_response"] in data["safe_response"]
    assert "IMPORTANT: This information is AI-generated" in data["safe_response"]
    assert len(data["alerts"]) == 0
    
    # Assert traces exist for all 7 agents
    assert len(data["traces"]) == 8
    expected_agents = [
        "InterceptorAgent",
        "DetectorAgent",
        "ValidatorAgent",
        "RiskAgent",
        "GeneratorAgent",
        "EvaluatorAgent",
        "MemoryAgent",
        "AlertAgent",
    ]
    actual_agents = [t["agent_name"] for t in data["traces"]]
    assert actual_agents == expected_agents
    print("test_analyze_low_risk: PASSED")

def test_analyze_high_risk():
    """
    Test POST /analyze with two hallucinations (HIGH risk, score 0.75).
    """
    payload = {
        "patient_id": "123",
        "query": "I have chest pain",
        "ai_response": "Your chest pain may be cardiopulmonary syndrome. Take ibuprofen-metformin twice daily."
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    # Assert HIGH risk details
    assert data["version"] == "0.3.0"
    assert data["risk_level"] == "CRITICAL"
    assert data["risk_score"] >= 0.80
    
    # Verify hallucinations
    assert len(data["hallucinations"]) == 2
    h_texts = {h["detected_text"] for h in data["hallucinations"]}
    assert "cardiopulmonary syndrome" in h_texts
    assert (
        "ibuprofen-metformin" in h_texts
        or "ibuprofen" in h_texts
        or "metformin" in h_texts
    )
    
    # Verify validations
    assert len(data["validated_claims"]) >= 2
    for v in data["validated_claims"]:
        assert v["is_valid"] is False
        
    # Verify safe response disclaimer is generated
    assert "emergency" in data["safe_response"].lower()
    assert any(
        phrase.lower() in data["safe_response"].lower()
        for phrase in [
            "potentially unsafe medical advice",
            "seek immediate",
            "emergency medical care",
            "blocked because",
        ]
    )
    
    # Verify alert is generated (for HIGH risk)
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["severity"] == "CRITICAL"
    
    # Verify traces are generated
    assert len(data["traces"]) == 8
    print("test_analyze_high_risk: PASSED")

def test_analyze_critical_risk():
    """
    Test POST /analyze with three hallucinations (CRITICAL risk, score 0.95).
    """
    payload = {
        "patient_id": "123",
        "query": "I feel extremely unwell",
        "ai_response": "You might have cardiopulmonary syndrome or neurovascular fever. Take ibuprofen-metformin."
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    # Assert CRITICAL risk details
    assert data["version"] == "0.3.0"
    assert data["risk_level"] == "CRITICAL"
    assert data["risk_score"] >= 0.80
    
    # Verify hallucinations
    assert len(data["hallucinations"]) == 3
    h_texts = {h["detected_text"] for h in data["hallucinations"]}
    assert "cardiopulmonary syndrome" in h_texts
    assert (
        "ibuprofen-metformin" in h_texts
        or "ibuprofen" in h_texts
        or "metformin" in h_texts
    )
    assert "neurovascular fever" in h_texts
    
    # Verify validations
    assert len(data["validated_claims"]) >= 3
    for v in data["validated_claims"]:
        assert v["is_valid"] is False
        
    # Verify safe response disclaimer is generated
    assert "MEDICAL EMERGENCY POSSIBLE" in data["safe_response"]
    assert "IMPORTANT: This information is AI-generated" in data["safe_response"]
    
    # Verify alert is generated (for CRITICAL risk)
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["severity"] == "CRITICAL"
    
    # Verify traces are generated
    assert len(data["traces"]) == 8
    print("test_analyze_critical_risk: PASSED")

if __name__ == "__main__":
    print("Running backend tests...")
    test_health()
    test_analyze_low_risk()
    test_analyze_high_risk()
    test_analyze_critical_risk()
    print("All tests passed successfully!")
