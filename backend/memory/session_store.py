"""
session_store.py
----------------
Phase 7 — Memory Layer: Abstract Interface

Defines the SessionStore abstract base class. All concrete implementations
(local JSON, Firebase Firestore, etc.) must implement this interface.

This decouples agent code from the storage backend — swapping to Firebase
requires only changing the concrete class injected into MemoryAgent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class SessionStore(ABC):
    """
    Abstract interface for ClinGuard AI session persistence.

    Implement this class to provide a concrete storage backend.
    Current implementation: LocalJSONSessionStore (patient_memory.py)
    Future implementation: FirestoreSessionStore
    """

    @abstractmethod
    def save_session(self, session: dict[str, Any]) -> str:
        """
        Persist a session record.

        Parameters
        ----------
        session : dict
            Must contain at minimum:
            - patient_id: str
            - query: str
            - ai_response: str
            - hallucinations: list[dict]
            - risk_score: float
            - risk_level: str
            - safe_response: str
            - timestamp: str (ISO 8601)

        Returns
        -------
        str
            The session_id assigned to this record.
        """
        ...

    @abstractmethod
    def get_patient_history(
        self,
        patient_id: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all sessions for a given patient, sorted newest-first.

        Parameters
        ----------
        patient_id : str
            The patient identifier to filter by.
        limit : int | None
            Maximum number of records to return (None = all).

        Returns
        -------
        list[dict]
            List of session records, sorted by timestamp descending.
        """
        ...

    @abstractmethod
    def get_recent_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Retrieve the most recent sessions across all patients.

        Parameters
        ----------
        limit : int
            Maximum number of records to return. Default 10.

        Returns
        -------
        list[dict]
            List of session records, sorted by timestamp descending.
        """
        ...
