from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import json

from backend.models.schemas import AnalyzeRequest, AnalyzeResponse
from backend.models.audit import AuditReport
from backend.orchestrator.pipeline import ClinGuardPipeline
from backend.repositories import AuditRepositoryV2
from backend.services import PdfExportService

router = APIRouter()

pipeline = ClinGuardPipeline()
audit_repository_v2 = AuditRepositoryV2()
pdf_export_service = PdfExportService()


@router.get("/health")
async def get_health():
    """
    Returns service health parameters, service name and version.
    """
    return {
        "status": "healthy",
        "service": "ClinGuard AI",
        "version": "0.3.0",
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def post_analyze(request: AnalyzeRequest):
    """
    Passes request payload through the modular multi-agent pipeline
    and returns safety evaluations.
    """
    try:
        return pipeline.run(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(exc)}",
        )


@router.get("/audit/{session_id}")
async def get_audit(session_id: str):
    report = audit_repository_v2.get_report(session_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Audit report not found",
        )

    return report


@router.get("/audit-history/{patient_id}")
async def get_audit_history(patient_id: str):
    return audit_repository_v2.get_patient_history(patient_id)


@router.get("/audit/{session_id}/export/json")
async def export_audit_json(session_id: str):
    report = audit_repository_v2.get_report(session_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Audit report not found",
        )

    # Convert stored dictionary back into an AuditReport model
    audit_report = AuditReport.model_validate(report)

    json_bytes = json.dumps(
        audit_report.model_dump(),
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{session_id}-audit.json"'
            ),
        },
    )


@router.get("/audit/{session_id}/export/pdf")
async def export_audit_pdf(session_id: str):
    report = audit_repository_v2.get_report(session_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Audit report not found",
        )

    # Convert stored dictionary back into an AuditReport model
    audit_report = AuditReport.model_validate(report)

    return Response(
        content=pdf_export_service.to_pdf_bytes(audit_report),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{session_id}-audit.pdf"'
            ),
        },
    )


@router.delete("/audit/{session_id}")
async def delete_audit(session_id: str):
    deleted = audit_repository_v2.delete_report(session_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Audit report not found",
        )

    return {
        "status": "success",
        "detail": "Audit report deleted",
    }