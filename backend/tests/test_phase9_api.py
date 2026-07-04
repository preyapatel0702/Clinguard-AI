from pathlib import Path
from fastapi.testclient import TestClient

from backend.api import endpoints
from backend.main import app
from backend.repositories import AuditRepositoryV2
from backend.models.audit import AuditReport


def _audit_report() -> AuditReport:
    return AuditReport(
        session_id="session_api_v2",
        patient_id="patient_api",
        timestamp="2026-06-21T10:00:00Z",
        session_metadata={"query": "q"},
        patient_information={"patient_id": "patient_api"},
        medical_entities={},
        hallucinations=[],
        validated_claims=[],
        explanations=[],
        risk_assessment={"risk_level": "LOW", "risk_score": 0.2},
        safe_response="Safe response",
        evaluation_report=None,
        alerts=[],
        timeline=[],
        decision_trace=[],
    )


def test_audit_api_v2_endpoints(tmp_path: Path):
    repository = AuditRepositoryV2(tmp_path / "audits_v2.json")
    repository.save_report(_audit_report())
    endpoints.audit_repository_v2 = repository

    client = TestClient(app)

    # 1. Get Report
    audit = client.get("/audit/session_api_v2")
    assert audit.status_code == 200
    assert audit.json()["session_id"] == "session_api_v2"

    # 2. Get History
    history = client.get("/audit-history/patient_api")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["session_id"] == "session_api_v2"
    assert history.json()[0]["risk_level"] == "LOW"

    # 3. JSON Export
    json_export = client.get("/audit/session_api_v2/export/json")
    assert json_export.status_code == 200
    assert json_export.headers["content-type"] == "application/json"
    assert "session_api_v2" in json_export.text

    # 4. PDF Export
    pdf_export = client.get("/audit/session_api_v2/export/pdf")
    assert pdf_export.status_code == 200
    assert pdf_export.headers["content-type"] == "application/pdf"
    assert pdf_export.content.startswith(b"%PDF-")

    # 5. Delete Report
    delete_res = client.delete("/audit/session_api_v2")
    assert delete_res.status_code == 200
    assert delete_res.json()["status"] == "success"

    # 6. Verify Deletion
    audit_after = client.get("/audit/session_api_v2")
    assert audit_after.status_code == 404
