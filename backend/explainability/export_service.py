import json
import logging
from textwrap import wrap

from backend.models.schemas import AuditReport


logger = logging.getLogger("clinguard.observability")


class AuditExportService:
    def to_json_bytes(self, report: AuditReport | dict) -> bytes:
        logger.info("phase9.export_generation format=json")
        payload = report.model_dump() if isinstance(report, AuditReport) else report
        return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

    def to_pdf_bytes(self, report: AuditReport | dict) -> bytes:
        logger.info("phase9.export_generation format=pdf")
        payload = report.model_dump() if isinstance(report, AuditReport) else report
        lines = self._report_lines(payload)
        return self._simple_pdf(lines)

    def _report_lines(self, report: dict) -> list[str]:
        lines = [
            "ClinGuard-AI Clinical Audit Report",
            f"Session: {report.get('session_id', 'N/A')}",
            f"Patient: {report.get('patient_id', 'N/A')}",
            f"Timestamp: {report.get('timestamp', 'N/A')}",
            "",
            "Risk Assessment",
            f"Level: {report.get('risk_assessment', {}).get('risk_level', 'N/A')}",
            f"Final Score: {report.get('risk_assessment', {}).get('final_score', 'N/A')}",
            report.get("risk_assessment", {}).get("narrative", ""),
            "",
            "Validation Results",
        ]

        for validation in report.get("validation_results", []):
            status = "SUPPORTED" if validation.get("is_valid") else "UNSUPPORTED"
            lines.append(
                f"- {validation.get('claim_text') or validation.get('claim_id')}: "
                f"{status} ({validation.get('confidence')})"
            )

        lines.extend(["", "Safe Response"])
        lines.extend(wrap(report.get("generated_safe_response", ""), width=92))
        return lines

    def _simple_pdf(self, lines: list[str]) -> bytes:
        escaped_lines = []
        for line in lines:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            escaped_lines.append(safe)

        content_parts = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        for index, line in enumerate(escaped_lines[:48]):
            if index == 0:
                content_parts.append(f"({line}) Tj")
            else:
                content_parts.append(f"T* ({line}) Tj")
        content_parts.append("ET")
        stream = "\n".join(content_parts).encode("latin-1", errors="replace")

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
            + stream + b"\nendstream",
        ]

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for number, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{number} 0 obj\n".encode("ascii"))
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        return bytes(pdf)
