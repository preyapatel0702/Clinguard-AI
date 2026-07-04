from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Core clinical claim schema
# ---------------------------------------------------------------------------

class MedicalClaim(BaseModel):
    claim_id: str = Field(..., description="Unique identifier for the claim")
    text: str = Field(..., description="The medical claim text extracted")
    category: str = Field(..., description="E.g., diagnosis, medication, symptom")
    confidence: float = Field(..., description="Confidence score of the extraction")


# ---------------------------------------------------------------------------
# Hallucination detection
# ---------------------------------------------------------------------------

class HallucinationResult(BaseModel):
    is_hallucination: bool = Field(..., description="Whether a hallucination was detected")
    detected_text: str = Field(..., description="The specific text segment flagged as hallucinated")
    confidence_score: float = Field(..., description="Confidence score of hallucination detection")
    details: str = Field(..., description="Details/reasoning for the detection")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    claim_id: str = Field(..., description="Identifier of the claim being validated")
    claim_text: Optional[str] = Field(
        default=None,
        description="Original claim text being validated",
    )
    is_valid: bool = Field(..., description="Whether the claim is medically valid/verifiable")
    source: str = Field(..., description="Reference source used for validation")
    confidence: float = Field(..., description="Confidence of the validation verdict")
    reasoning: str = Field(default="", description="Reasoning for validation verdict")


# ---------------------------------------------------------------------------
# Phase 9 - Explainability, Audit, and Decision Intelligence
# ---------------------------------------------------------------------------

class ClaimExplanation(BaseModel):
    claim_id: str
    claim_text: Optional[str] = None
    validation_status: str
    confidence_score: float
    evidence_source: str
    reasoning: str
    related_entities: List[str] = Field(default_factory=list)


class AgentTimelineEvent(BaseModel):
    agent: str
    timestamp: str
    duration_ms: float
    status: str


class DecisionTraceNode(BaseModel):
    agent: str
    status: str
    execution_time_ms: float
    timestamp: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)


class DecisionTrace(BaseModel):
    nodes: List[DecisionTraceNode] = Field(default_factory=list)


class RiskExplanation(BaseModel):
    severity_score: float = 0.0
    urgency_score: float = 0.0
    vulnerability_score: float = 0.0
    hallucination_boost: float = 0.0
    raw_score: float = 0.0
    final_score: float = 0.0
    risk_level: str = "LOW"
    narrative: str = ""

# ---------------------------------------------------------------------------
# Phase 6 — Agent Self-Evaluation
# ---------------------------------------------------------------------------

class EvaluationReport(BaseModel):
    """Self-evaluation report produced by EvaluatorAgent."""
    coverage_score: float = Field(..., description="Hallucination coverage score (0–100)")
    consistency_score: float = Field(..., description="Validation consistency score (0–100)")
    risk_consistency_score: float = Field(..., description="Risk level vs. response consistency score (0–100)")
    safety_score: float = Field(..., description="Safety guidance completeness score (0–100)")
    overall_score: float = Field(..., description="Weighted overall score (0–100)")
    passed: bool = Field(..., description="True if overall_score >= 80")
    failure_reasons: List[str] = Field(
        default_factory=list,
        description="List of reasons the evaluation failed, if applicable"
    )


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertPayload(BaseModel):
    alert_id: str = Field(..., description="Unique identifier for the alert")
    severity: str = Field(..., description="Severity level: INFO, WARNING, CRITICAL")
    message: str = Field(..., description="Alert description")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the alert")



class AuditReport(BaseModel):
    session_id: str
    patient_id: str
    timestamp: str
    patient_context: Dict[str, Any]
    detected_entities: Dict[str, List[dict]]
    detected_hallucinations: List[HallucinationResult]
    validation_results: List[ValidationResult]
    explanations: List[ClaimExplanation]
    risk_assessment: RiskExplanation
    generated_safe_response: str
    evaluation_metrics: Optional[EvaluationReport] = None
    alerts: List[AlertPayload]
    agent_timeline: List[AgentTimelineEvent]
    decision_trace: DecisionTrace


# ---------------------------------------------------------------------------
# Phase 4 — Risk Intelligence Engine
# ---------------------------------------------------------------------------

class RiskBreakdown(BaseModel):
    """Detailed breakdown of how the final risk score was computed."""
    severity_score: float = Field(..., description="Symptom severity score (0.0–1.0)")
    urgency_score: float = Field(..., description="Urgency score derived from symptom category (0.0–1.0)")
    vulnerability_score: float = Field(..., description="Patient vulnerability score (0.0–1.0)")
    hallucination_boost: float = Field(default=0.0, description="Additional boost from detected hallucinations")
    raw_score: float = Field(..., description="Weighted score before hallucination boost")
    final_score: float = Field(..., description="Final risk score after hallucination boost (capped at 1.0)")
    risk_level: str = Field(..., description="Derived risk level: LOW, MODERATE, HIGH, CRITICAL")


class RiskAssessment(BaseModel):
    risk_level: str = Field(..., description="Safety risk level, e.g., LOW, MODERATE, HIGH, CRITICAL")
    risk_score: float = Field(..., description="Risk score from 0.0 to 1.0")
    reasoning: str = Field(..., description="Reasoning behind the risk level and score")
    breakdown: Optional[RiskBreakdown] = Field(default=None, description="Detailed score breakdown")


# ---------------------------------------------------------------------------
# Phase 5 — Safe Response Generator
# ---------------------------------------------------------------------------

class SafeResponse(BaseModel):
    """Legacy safe response object (kept for backward compatibility)."""
    original_response: str = Field(..., description="The original response from the AI")
    safe_response: str = Field(..., description="The modified, safe response or original if risk is low")
    modified: bool = Field(..., description="Whether the response was modified")


class SafeResponseMetadata(BaseModel):
    """Rich metadata produced by the intelligent SafeResponseGenerator."""
    original_response: str = Field(..., description="The raw AI response before safety processing")
    safe_response: str = Field(..., description="Processed, safety-compliant response text")
    safety_reason: str = Field(..., description="Explanation of why and how the response was modified")
    confidence: float = Field(..., description="Generator confidence score (0.0–1.0)")
    modifications_made: List[str] = Field(
        default_factory=list,
        description="List of specific modifications applied"
    )



# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

class AgentTrace(BaseModel):
    agent_name: str = Field(..., description="Name of the agent executing the step")
    timestamp: str = Field(..., description="ISO 8601 timestamp of execution")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    status: str = Field(..., description="Execution status, e.g., SUCCESS, FAILED")


class AgentMessage(BaseModel):
    sender: str = Field(..., description="Sender agent name")
    receiver: str = Field(..., description="Receiver agent name")
    payload: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the message")


class MedicalEntity(BaseModel):
    text: str
    label: str
    score: float

# ---------------------------------------------------------------------------
# Pipeline Context
# ---------------------------------------------------------------------------

class PipelineContext(BaseModel):
    # Request fields
    patient_id: str = Field(..., description="Identifier for the patient")
    query: str = Field(..., description="User query/symptoms")
    ai_response: str = Field(..., description="Raw AI response being analyzed")

    # Optional patient demographics (used by VulnerabilityCalculator)
    patient_age: Optional[int] = Field(default=None, description="Patient age in years")
    comorbidities: List[str] = Field(
        default_factory=list,
        description="Known comorbidities, e.g., ['diabetes', 'hypertension']"
    )

    # Pipeline state
    claims: List[MedicalClaim] = Field(default_factory=list, description="Extracted medical claims")
    hallucinations: List[HallucinationResult] = Field(
        default_factory=list, description="Detected hallucinations"
    )
    hallucination_detected: bool = Field(
        default=False,
        description="True if any detected hallucination has is_hallucination=True",
    )
    validations: List[ValidationResult] = Field(
        default_factory=list, description="Validation results for claims"
    )

    # Risk
    risk_score: float = Field(default=0.0, description="Overall computed risk score")
    risk_level: str = Field(default="LOW", description="Overall risk level: LOW, MODERATE, HIGH, CRITICAL")
    risk_breakdown: Optional[RiskBreakdown] = Field(
        default=None, description="Detailed risk score breakdown"
    )
    medical_entities: Dict[str, List[dict]] = Field(
        default_factory=lambda: {
            "drugs": [],
            "diseases": [],
            "symptoms": []
        }
    )

    # Response
    safe_response: str = Field(default="", description="The final safe/mitigated response text")

    # Evaluation
    evaluation_report: Optional[EvaluationReport] = Field(
        default=None, description="Self-evaluation report from EvaluatorAgent"
    )

    # Output
    alerts: List[AlertPayload] = Field(default_factory=list, description="Triggered alerts")
    traces: List[AgentTrace] = Field(default_factory=list, description="Agent execution traces")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata dictionary for state and messaging history"
    )


# ---------------------------------------------------------------------------
# API Request / Response
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    patient_id: str
    query: str
    ai_response: str
    patient_age: Optional[int] = Field(default=None, description="Patient age (optional)")
    comorbidities: List[str] = Field(
        default_factory=list,
        description="Patient comorbidities, e.g., ['diabetes', 'hypertension']"
    )


class AnalyzeResponse(BaseModel):
    version: str
    risk_level: str
    risk_score: float
    risk_breakdown: Optional[RiskBreakdown] = None
    hallucinations: List[HallucinationResult]
    hallucination_detected: bool = Field(
        default=False,
        description="True if any hallucination was detected during analysis",
    )
    validated_claims: List[ValidationResult]
    safe_response: str
    evaluation_report: Optional[EvaluationReport] = None
    alerts: List[AlertPayload]
    traces: List[AgentTrace]
    memory_saved: bool = Field(default=False, description="Whether session was persisted to memory")
    medical_entities: Dict[str, List[dict]] = Field(
        default_factory=dict
    )
    explanations: List[ClaimExplanation] = Field(default_factory=list)
    agent_timeline: List[AgentTimelineEvent] = Field(default_factory=list)
    decision_trace: Optional[DecisionTrace] = None
    risk_explanation: Optional[RiskExplanation] = None
    audit_report: Optional[AuditReport] = None
    audit_exports: Dict[str, str] = Field(default_factory=dict)

    # Phase 9 — rich explainability audit (new models from backend.models.audit)
    phase9_audit: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Phase 9 rich audit report with explanations, timeline, and decision traces.",
    )