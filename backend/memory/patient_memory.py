"""
patient_memory.py
-----------------
Phase 7 — Memory Layer: Local JSON Implementation

Provides LocalJSONSessionStore, a concrete SessionStore backed by a local
JSON file at `backend/data/sessions.json`.

Thread-safe via threading.Lock for concurrent FastAPI requests.

Designed so the interface (SessionStore) never changes when migrating to
Firebase Firestore — only swap the concrete class.

Migration to Firebase
---------------------
Create `backend/memory/firestore_store.py`:

    from backend.memory.session_store import SessionStore
    from google.cloud import firestore

    class FirestoreSessionStore(SessionStore):
        def __init__(self, collection: str = "sessions"):
            self._db = firestore.Client()
            self._col = self._db.collection(collection)

        def save_session(self, session):
            doc = self._col.add(session)
            return doc[1].id

        def get_patient_history(self, patient_id, limit=None):
            q = self._col.where("patient_id", "==", patient_id).order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            )
            if limit:
                q = q.limit(limit)
            return [d.to_dict() | {"session_id": d.id} for d in q.stream()]

        def get_recent_sessions(self, limit=10):
            q = self._col.order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            ).limit(limit)
            return [d.to_dict() | {"session_id": d.id} for d in q.stream()]

Then in MemoryAgent.__init__:
    self._store = FirestoreSessionStore()
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.memory.session_store import SessionStore

logger = logging.getLogger("clinguard.observability")

# Default data file path — relative to the backend package root
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DEFAULT_SESSIONS_FILE = _DEFAULT_DATA_DIR / "sessions.json"


class LocalJSONSessionStore(SessionStore):
    """
    Thread-safe JSON-file-backed implementation of SessionStore.

    All sessions are stored as a JSON array in *file_path*.
    New sessions are appended; reads load the entire file.

    Parameters
    ----------
    file_path : Path | str | None
        Path to the JSON sessions file. Defaults to backend/data/sessions.json.
    """

    def __init__(self, file_path: Optional[Path | str] = None) -> None:
        self._file_path = Path(file_path) if file_path else _DEFAULT_SESSIONS_FILE
        self._lock = threading.Lock()
        self._ensure_file()
        self._sessions = self._load()
        logger.info(f"[LocalJSONSessionStore] initialised file={self._file_path}")

    # -------------------------------------------------------------------------
    # SessionStore interface
    # -------------------------------------------------------------------------

    def save_session(self, session: dict[str, Any]) -> str:
        session_id = session.get("session_id") or f"session_{uuid.uuid4().hex}"
        session["session_id"] = session_id

        if "timestamp" not in session:
            session["timestamp"] = datetime.now(timezone.utc).isoformat()

        with self._lock:
            sessions = self._load()
            sessions.append(session)
            self._save(sessions)
            self._sessions = sessions

        logger.info(
            f"[LocalJSONSessionStore] saved session_id={session_id} "
            f"patient_id={session.get('patient_id', 'unknown')}"
        )

        return session_id

    def get_patient_history(
        self,
        patient_id: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Return all sessions for *patient_id*, sorted newest-first.
        """
        with self._lock:
            sessions = self._load()
            self._sessions = sessions

        filtered = [s for s in sessions if s.get("patient_id") == patient_id]
        filtered.sort(key=lambda s: s.get("timestamp", ""), reverse=True)

        if limit is not None:
            filtered = filtered[:limit]

        logger.info(
            f"[LocalJSONSessionStore] get_patient_history "
            f"patient_id={patient_id} results={len(filtered)}"
        )
        return filtered

    def get_recent_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the *limit* most recent sessions across all patients.
        """
        with self._lock:
            sessions = self._load()
            self._sessions = sessions

        sessions.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
        result = sessions[:limit]

        logger.info(
            f"[LocalJSONSessionStore] get_recent_sessions limit={limit} results={len(result)}"
        )
        return result

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _ensure_file(self) -> None:
        """Create parent directories and empty JSON array file if not present."""
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("[]", encoding="utf-8")
            logger.info(f"[LocalJSONSessionStore] created new file {self._file_path}")

    def _load(self) -> list[dict[str, Any]]:
        """Load and return sessions list from the JSON file (caller holds lock)."""
        try:
            text = self._file_path.read_text(encoding="utf-8").strip()
            if not text:
                return []
            return json.loads(text)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"[LocalJSONSessionStore] load error: {exc}")
            return []

    def _save(self, sessions: list[dict[str, Any]]) -> None:
        """Serialise and write sessions list (caller holds lock)."""
        try:
            self._file_path.write_text(
                json.dumps(sessions, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error(f"[LocalJSONSessionStore] save error: {exc}")
            raise
