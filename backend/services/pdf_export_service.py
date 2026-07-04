"""
pdf_export_service.py
---------------------
Phase 9 — ReportLab PDF Clinical Audit Export

Generates a professional multi-page PDF containing:
  • Executive Summary
  • Detected Medical Entities
  • Hallucinations
  • Validated Claims
  • Risk Assessment
  • Generated Safe Response
  • Agent Timeline
  • Decision Trace
  • Clinical Recommendations
  • Generation Timestamp

Falls back to a simple text-based PDF when ReportLab is unavailable
so the service never hard-fails.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.models.audit import AuditReport

logger = logging.getLogger("clinguard.phase9.pdf_export")

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    _HAS_REPORTLAB = True
except ImportError:  # pragma: no cover
    _HAS_REPORTLAB = False
    logger.warning(
        "reportlab not installed — PDF export will produce a minimal fallback."
    )


class PdfExportService:
    """Generate a clinical-grade PDF from an AuditReport."""

    def to_pdf_bytes(self, report: AuditReport | dict) -> bytes:
        """Render *report* as a PDF and return raw bytes."""
        if isinstance(report, dict):
            report = AuditReport(**report)

        if _HAS_REPORTLAB:
            return self._reportlab_pdf(report)
        return self._fallback_pdf(report)

    # ------------------------------------------------------------------
    # ReportLab implementation
    # ------------------------------------------------------------------

    def _reportlab_pdf(self, report: AuditReport) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            title=f"ClinGuard-AI Audit — {report.session_id}",
            author="ClinGuard-AI Phase 9",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "AuditTitle",
            parent=styles["Title"],
            fontSize=18,
            spaceAfter=6 * mm,
            textColor=colors.HexColor("#1a237e"),
        )
        heading_style = ParagraphStyle(
            "AuditHeading",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
            textColor=colors.HexColor("#283593"),
        )
        body_style = ParagraphStyle(
            "AuditBody",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
        )
        small_style = ParagraphStyle(
            "AuditSmall",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.grey,
        )

        story: list = []

        # Title
        story.append(Paragraph("ClinGuard-AI — Clinical Audit Report", title_style))
        story.append(Spacer(1, 2 * mm))

        # ----- Executive Summary -----
        story.append(Paragraph("Executive Summary", heading_style))
        risk_info = report.risk_assessment
        risk_level = risk_info.get("risk_level", "N/A") if isinstance(risk_info, dict) else "N/A"
        risk_score = risk_info.get("risk_score", risk_info.get("final_score", "N/A")) if isinstance(risk_info, dict) else "N/A"
        summary_data = [
            ["Session ID", report.session_id],
            ["Patient ID", report.patient_id],
            ["Timestamp", report.timestamp],
            ["Risk Level", str(risk_level)],
            ["Risk Score", str(risk_score)],
            ["Hallucinations", str(len(report.hallucinations))],
            ["Validated Claims", str(len(report.validated_claims))],
            ["Explanations", str(len(report.explanations))],
        ]
        story.append(self._make_table(summary_data))

        # ----- Medical Entities -----
        story.append(Paragraph("Detected Medical Entities", heading_style))
        entity_rows: List[List[str]] = [["Category", "Entity", "Score"]]
        for cat in ("drugs", "diseases", "symptoms"):
            for ent in report.medical_entities.get(cat, []):
                entity_rows.append([
                    cat.title(),
                    str(ent.get("text", "")),
                    f"{ent.get('score', 0):.3f}",
                ])
        if len(entity_rows) > 1:
            story.append(self._make_table(entity_rows, header=True))
        else:
            story.append(Paragraph("No medical entities detected.", body_style))

        # ----- Hallucinations -----
        story.append(Paragraph("Hallucinations", heading_style))
        if report.hallucinations:
            hal_rows: List[List[str]] = [["Text", "Confidence", "Details"]]
            for h in report.hallucinations:
                if h.get("is_hallucination"):
                    hal_rows.append([
                        str(h.get("detected_text", "")),
                        f"{h.get('confidence_score', 0):.2f}",
                        str(h.get("details", ""))[:80],
                    ])
            if len(hal_rows) > 1:
                story.append(self._make_table(hal_rows, header=True))
            else:
                story.append(Paragraph("No active hallucinations.", body_style))
        else:
            story.append(Paragraph("No hallucinations analysed.", body_style))

        # ----- Validated Claims -----
        story.append(Paragraph("Validated Claims", heading_style))
        if report.validated_claims:
            claim_rows: List[List[str]] = [["Claim", "Valid", "Source", "Confidence"]]
            for v in report.validated_claims:
                claim_rows.append([
                    str(v.get("claim_text", v.get("claim_id", "")))[:50],
                    "Yes" if v.get("is_valid") else "No",
                    str(v.get("source", ""))[:40],
                    f"{v.get('confidence', 0):.2f}",
                ])
            story.append(self._make_table(claim_rows, header=True))
        else:
            story.append(Paragraph("No claims validated.", body_style))

        # ----- Risk Assessment -----
        story.append(Paragraph("Risk Assessment", heading_style))
        if isinstance(risk_info, dict):
            risk_rows = [[k.replace("_", " ").title(), str(v)] for k, v in risk_info.items()]
            story.append(self._make_table(risk_rows))
        else:
            story.append(Paragraph("No risk data available.", body_style))

        # ----- Safe Response -----
        story.append(Paragraph("Generated Safe Response", heading_style))
        safe_text = (report.safe_response or "N/A").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe_text, body_style))

        # ----- Agent Timeline -----
        story.append(Paragraph("Agent Timeline", heading_style))
        if report.timeline:
            tl_rows: List[List[str]] = [["Agent", "Duration (ms)", "Status", "Actions"]]
            for evt in report.timeline:
                actions_str = "; ".join(evt.actions_performed[:3])
                tl_rows.append([
                    evt.agent_name,
                    f"{evt.execution_time_ms:.2f}",
                    evt.status,
                    actions_str[:60],
                ])
            story.append(self._make_table(tl_rows, header=True))
        else:
            story.append(Paragraph("No timeline data.", body_style))

        # ----- Decision Trace -----
        story.append(Paragraph("Decision Trace", heading_style))
        if report.decision_trace:
            dt_rows: List[List[str]] = [["Agent", "Action", "Confidence", "Evidence"]]
            for dt in report.decision_trace:
                evidence_str = "; ".join(dt.evidence[:2])
                dt_rows.append([
                    dt.agent_name,
                    dt.action,
                    f"{dt.confidence:.2f}",
                    evidence_str[:60],
                ])
            story.append(self._make_table(dt_rows, header=True))
        else:
            story.append(Paragraph("No decision traces recorded.", body_style))

        # ----- Clinical Recommendations -----
        story.append(Paragraph("Clinical Recommendations", heading_style))
        recommendations = self._generate_recommendations(report)
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", body_style))

        # ----- Generation Timestamp -----
        story.append(Spacer(1, 6 * mm))
        story.append(
            Paragraph(
                f"Report generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                small_style,
            )
        )
        story.append(
            Paragraph(
                "ClinGuard-AI — Healthcare AI Safety Platform — Phase 9 Audit",
                small_style,
            )
        )

        doc.build(story)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Table helper
    # ------------------------------------------------------------------

    @staticmethod
    def _make_table(
        data: List[List[str]],
        header: bool = False,
    ) -> Table:
        """Create a styled Platypus Table."""
        table = Table(data, hAlign="LEFT", repeatRows=1 if header else 0)
        style_cmds: list = [
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        if header and len(data) > 1:
            style_cmds.extend([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaf6")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ])
        table.setStyle(TableStyle(style_cmds))
        return table

    # ------------------------------------------------------------------
    # Clinical recommendations
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_recommendations(report: AuditReport) -> List[str]:
        """Auto-generate clinical recommendations based on audit findings."""
        recs: List[str] = []
        risk_info = report.risk_assessment if isinstance(report.risk_assessment, dict) else {}
        risk_level = risk_info.get("risk_level", "LOW")

        active_hallucinations = [
            h for h in report.hallucinations if h.get("is_hallucination")
        ]

        if risk_level in ("HIGH", "CRITICAL"):
            recs.append(
                "URGENT: High or critical risk detected. "
                "Immediate clinical review is recommended."
            )

        if active_hallucinations:
            recs.append(
                f"{len(active_hallucinations)} hallucinated medical claim(s) detected. "
                "All flagged information should be independently verified before clinical use."
            )

        rejected = [v for v in report.validated_claims if not v.get("is_valid")]
        if rejected:
            recs.append(
                f"{len(rejected)} medical claim(s) could not be validated. "
                "Cross-reference with authoritative medical databases."
            )

        eval_report = report.evaluation_report
        if isinstance(eval_report, dict) and not eval_report.get("passed", True):
            recs.append(
                "Pipeline self-evaluation did not pass. "
                "Exercise additional caution with all generated content."
            )

        if not recs:
            recs.append(
                "No elevated risk factors identified. Standard clinical "
                "judgement should still be applied."
            )

        recs.append(
            "This report is AI-generated and intended for clinical decision "
            "support only. Always consult a licensed healthcare professional."
        )

        return recs

    # ------------------------------------------------------------------
    # Fallback PDF (no ReportLab)
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_pdf(report: AuditReport) -> bytes:
        """Produce a minimal valid PDF when ReportLab is not installed."""
        lines = [
            "ClinGuard-AI Clinical Audit Report",
            f"Session: {report.session_id}",
            f"Patient: {report.patient_id}",
            f"Timestamp: {report.timestamp}",
            "",
            f"Risk Level: {report.risk_assessment.get('risk_level', 'N/A') if isinstance(report.risk_assessment, dict) else 'N/A'}",
            f"Hallucinations: {len(report.hallucinations)}",
            f"Claims: {len(report.validated_claims)}",
            f"Explanations: {len(report.explanations)}",
            "",
            "Safe Response:",
            report.safe_response or "N/A",
        ]

        escaped: list = []
        for line in lines:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            escaped.append(safe)

        content_parts = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        for idx, line in enumerate(escaped[:48]):
            if idx == 0:
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
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
            + stream + b"\nendstream",
        ]

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for num, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{num} 0 obj\n".encode())
            pdf.extend(obj)
            pdf.extend(b"\nendobj\n")

        xref_off = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
        pdf.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            pdf.extend(f"{off:010d} 00000 n \n".encode())
        pdf.extend(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_off}\n%%EOF\n".encode()
        )
        return bytes(pdf)
