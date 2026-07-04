from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.models.schemas import AuditReport


logger = logging.getLogger("clinguard.observability")

_DEFAULT_AUDIT_FILE = Path(__file__).resolve().parent.parent / "data" / "audit_reports.json"


class AuditRepository:
    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file_path = Path(file_path) if file_path else _DEFAULT_AUDIT_FILE
        self._lock = threading.Lock()
        self._ensure_file()

    def save(self, report: AuditReport) -> str:
        record = {
            "session_id": report.session_id,
            "patient_id": report.patient_id,
            "timestamp": report.timestamp or datetime.now(timezone.utc).isoformat(),
            "audit_report": report.model_dump(),
        }

        with self._lock:
            records = self._load()
            records = [r for r in records if r.get("session_id") != report.session_id]
            records.append(record)
            self._save(records)

        logger.info(
            "phase9.audit_repository saved session_id=%s patient_id=%s",
            report.session_id,
            report.patient_id,
        )
        return report.session_id

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            records = self._load()
        for record in records:
            if record.get("session_id") == session_id:
                return record.get("audit_report")
        return None

    def history(self, patient_id: str) -> list[dict[str, Any]]:
        with self._lock:
            records = self._load()

        results = [
            {
                "session_id": record.get("session_id"),
                "patient_id": record.get("patient_id"),
                "timestamp": record.get("timestamp"),
                "risk_level": record.get("audit_report", {}).get("risk_assessment", {}).get("risk_level"),
                "risk_score": record.get("audit_report", {}).get("risk_assessment", {}).get("final_score"),
            }
            for record in records
            if record.get("patient_id") == patient_id
        ]
        results.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
        return results

    def _ensure_file(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict[str, Any]]:
        try:
            raw = self._file_path.read_text(encoding="utf-8").strip()
            return json.loads(raw) if raw else []
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("phase9.audit_repository load_error=%s", exc)
            return []

    def _save(self, records: list[dict[str, Any]]) -> None:
        self._file_path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
