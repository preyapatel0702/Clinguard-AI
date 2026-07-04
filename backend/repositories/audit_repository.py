"""
audit_repository.py
-------------------
Phase 9 — Thread-safe Audit Report Persistence
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.models.audit import AuditReport, AuditSummary

logger = logging.getLogger("clinguard.phase9.repository")

_DEFAULT_DATA_FILE: Path = (
    Path(__file__).resolve().parent.parent / "data" / "audit_reports.json"
)


class AuditRepositoryV2:
    """Thread-safe JSON-file-backed audit report repository."""

    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path: Path = Path(file_path) if file_path else _DEFAULT_DATA_FILE
        self._lock = threading.Lock()
        self._ensure_file()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save_report(self, report: AuditReport) -> str:
        """Persist report (upsert by session_id)."""
        record = self._report_to_record(report)

        with self._lock:
            records = self._load()
            records = [
                r for r in records
                if r.get("session_id") != report.session_id
            ]
            records.append(record)
            self._save(records)

        logger.info(
            "audit_repository.save_report session_id=%s patient_id=%s",
            report.session_id,
            report.patient_id,
        )

        return report.session_id

    def get_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the stored audit report dictionary.
        """

        with self._lock:
            records = self._load()

        for record in records:
            if record.get("session_id") == session_id:
                return record["audit_report"]

        return None

    def get_patient_history(self, patient_id: str) -> List[AuditSummary]:
        """Return summaries for all reports belonging to a patient."""

        with self._lock:
            records = self._load()

        summaries: List[AuditSummary] = []

        for record in records:
            if record.get("patient_id") != patient_id:
                continue

            audit = record.get("audit_report", {})
            risk = audit.get("risk_assessment", {})

            summaries.append(
                AuditSummary(
                    session_id=record.get("session_id", ""),
                    patient_id=record.get("patient_id", ""),
                    timestamp=record.get("timestamp", ""),
                    risk_level=risk.get("risk_level"),
                    risk_score=risk.get(
                        "risk_score",
                        risk.get("final_score"),
                    ),
                    hallucination_count=len(audit.get("hallucinations", [])),
                    claim_count=len(audit.get("validated_claims", [])),
                    passed_evaluation=(
                        audit.get("evaluation_report") or {}
                    ).get("passed"),
                )
            )

        summaries.sort(
            key=lambda summary: summary.timestamp or "",
            reverse=True,
        )

        return summaries

    def delete_report(self, session_id: str) -> bool:
        """Delete a report."""

        with self._lock:
            records = self._load()
            original_count = len(records)

            records = [
                r
                for r in records
                if r.get("session_id") != session_id
            ]

            deleted = len(records) < original_count

            if deleted:
                self._save(records)

        if deleted:
            logger.info(
                "audit_repository.delete_report session_id=%s deleted",
                session_id,
            )
        else:
            logger.warning(
                "audit_repository.delete_report session_id=%s not_found",
                session_id,
            )

        return deleted

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _report_to_record(report: AuditReport) -> Dict[str, Any]:
        return {
            "session_id": report.session_id,
            "patient_id": report.patient_id,
            "timestamp": report.timestamp
            or datetime.now(timezone.utc).isoformat(),
            "audit_report": report.model_dump(),
        }

    def _ensure_file(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self._file_path.exists():
            self._file_path.write_text(
                "[]",
                encoding="utf-8",
            )

    def _load(self) -> List[Dict[str, Any]]:
        try:
            raw = self._file_path.read_text(
                encoding="utf-8",
            ).strip()

            return json.loads(raw) if raw else []

        except (OSError, json.JSONDecodeError) as exc:
            logger.error(
                "audit_repository._load error=%s",
                exc,
            )
            return []

    def _save(self, records: List[Dict[str, Any]]) -> None:
        self._file_path.write_text(
            json.dumps(
                records,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )