"""
chat_schemas.py
----------------
Compatibility schemas for the frontend Chat client (POST /chat/messages).

These models are additive only — they do not modify or replace anything in
``backend.models.schemas``. They exist purely to translate the chat-shaped
request/response contract the frontend expects into the existing
``AnalyzeRequest`` / ``AnalyzeResponse`` contract used by ``ClinGuardPipeline``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat turn, OpenAI-style ({role, content})."""

    role: str = Field(default="user", description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    """
    Request payload sent by the frontend Chat client.

    Supports two shapes for maximum compatibility with existing frontend code:
      1. ``messages``: a full chat history (OpenAI-style list of role/content).
      2. ``message``: a single flat string for simple chat clients.

    At least one of ``messages`` or ``message`` must be provided.
    """

    messages: Optional[List[ChatMessage]] = Field(
        default=None, description="Chat history; the latest user message is analyzed."
    )
    message: Optional[str] = Field(
        default=None, description="Flat single-message alternative to `messages`."
    )

    patient_id: Optional[str] = Field(
        default=None, description="Identifier for the patient/user (optional)."
    )
    session_id: Optional[str] = Field(
        default=None, description="Chat session identifier, echoed back if provided."
    )
    patient_age: Optional[int] = Field(default=None, description="Patient age (optional)")
    comorbidities: List[str] = Field(
        default_factory=list,
        description="Patient comorbidities, e.g., ['diabetes', 'hypertension']",
    )


class ChatResponse(BaseModel):
    """
    Response payload returned to the frontend Chat client.

    ``reply`` carries the assistant's message text (sourced from
    ``AnalyzeResponse.safe_response``). The remaining fields surface the
    underlying safety analysis for clients that want it, without forcing
    every caller to parse the full ``AnalyzeResponse``.
    """

    role: str = "assistant"
    reply: str
    session_id: Optional[str] = None
    risk_level: str
    risk_score: float
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Full underlying AnalyzeResponse payload, for clients that need it.",
    )