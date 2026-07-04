"""
audit.py
--------
Phase 9 — Explainability & Clinical Audit Models

Pydantic v2 models for the explainability and clinical audit subsystem.
These models coexist with the existing ``schemas.py`` definitions;
the pipeline populates both old and new models for full backward
compatibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------

class ClaimExplanation(BaseModel):
    """Structured explanation for a single pipeline finding."""

    explanation_id: str = Field(
        default_factory=lambda: f"expl_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for this explanation.",
    )
    category: str = Field(
        ...,
        description=(
            "Kind of finding: hallucination_detection, validation_outcome, "
            "risk_calculation, response_modification."
        ),
    )
    title: str = Field(..., description="Human-readable one-line summary.")
    reasoning: str = Field(..., description="Detailed reasoning behind the finding.")
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence items (text fragments, entity names, etc.).",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score 0–1."
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 generation timestamp.",
    )


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class TimelineEvent(BaseModel):
    """Chronological entry for a single agent execution."""

    agent_name: str = Field(..., description="Name of the pipeline agent.")
    start_time: str = Field(..., description="ISO-8601 start timestamp.")
    end_time: str = Field(..., description="ISO-8601 end timestamp.")
    execution_time_ms: float = Field(
        ..., description="Wall-clock execution duration in milliseconds."
    )
    status: str = Field(..., description="Execution status: SUCCESS or FAILED.")
    actions_performed: List[str] = Field(
        default_factory=list,
        description="Human-readable actions the agent performed.",
    )


# ---------------------------------------------------------------------------
# Decision Trace
# ---------------------------------------------------------------------------

class DecisionTrace(BaseModel):
    """Single granular decision recorded during pipeline execution."""

    decision_id: str = Field(
        default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for this decision.",
    )
    agent_name: str = Field(..., description="Agent that made the decision.")
    action: str = Field(
        ...,
        description=(
            "Verb-noun label, e.g. extracted_medication, hallucination_detected, "
            "validated_claim, rejected_claim, calculated_severity, "
            "determined_risk_level, modified_response, inserted_disclaimer."
        ),
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence for this decision.",
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score 0–1."
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp when the decision was recorded.",
    )


# ---------------------------------------------------------------------------
# Audit Report
# ---------------------------------------------------------------------------

class AuditReport(BaseModel):
    """Complete clinical audit report assembled after pipeline execution."""

    session_id: str = Field(..., description="Pipeline session identifier.")
    patient_id: str = Field(..., description="Patient identifier.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Report generation timestamp.",
    )

    # Session / patient metadata
    session_metadata: Dict[str, Any] = Field(default_factory=dict)
    patient_information: Dict[str, Any] = Field(default_factory=dict)

    # Pipeline data
    medical_entities: Dict[str, List[dict]] = Field(default_factory=dict)
    hallucinations: List[Dict[str, Any]] = Field(default_factory=list)
    validated_claims: List[Dict[str, Any]] = Field(default_factory=list)

    # Explainability
    explanations: List[ClaimExplanation] = Field(default_factory=list)

    # Risk
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)

    # Response
    safe_response: str = Field(default="")

    # Evaluation
    evaluation_report: Optional[Dict[str, Any]] = None

    # Alerts
    alerts: List[Dict[str, Any]] = Field(default_factory=list)

    # Timeline & trace
    timeline: List[TimelineEvent] = Field(default_factory=list)
    decision_trace: List[DecisionTrace] = Field(default_factory=list)

    # Timestamps
    pipeline_started_at: Optional[str] = None
    pipeline_completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Audit Summary (lightweight, used for history listings)
# ---------------------------------------------------------------------------

class AuditSummary(BaseModel):
    """Lightweight projection of an AuditReport for list endpoints."""

    session_id: str
    patient_id: str
    timestamp: str
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    hallucination_count: int = 0
    claim_count: int = 0
    passed_evaluation: Optional[bool] = None
