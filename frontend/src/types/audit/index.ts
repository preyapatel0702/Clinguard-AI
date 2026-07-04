// Domain types for the Audit module.
//
// These model a single clinical AI decision audit ("audit report"), keyed
// by session, plus the lighter-weight history list returned per patient.
// They intentionally live apart from the generic `AuditLogEntry` in
// `types/index.ts` (which models platform access-log events on the
// Dashboard) — this module covers session-level decision auditing:
// timeline, decision trace, explanation, hallucination and validation
// findings.

import type { Severity } from "../index";

/** Risk classification for an audited session. Reuses the shared Severity
 * scale so the existing `severityToBadgeColor` mapping applies. */
export type AuditRiskLevel = Severity;

export type AuditOutcome =
  | "approved"
  | "flagged"
  | "rejected"
  | "pending_review";

/* ------------------------------------------------------------------ */
/*  History (list) — GET /audit-history/{patient_id}                   */
/* ------------------------------------------------------------------ */

// NOTE: `patientName` and `modelName` have no equivalent field anywhere in
// the backend (models/audit.py AuditSummary only has session/patient IDs,
// timestamp, risk level/score, and counts) - left optional and always
// undefined when populated from the real API.
export interface AuditHistoryEntry {
  sessionId: string;
  patientId: string;
  patientName?: string;
  createdAt: string; // ISO 8601
  riskLevel: AuditRiskLevel;
  outcome: AuditOutcome;
  modelName?: string;
  summary: string;
  hallucinationCount: number;
  validationFailureCount: number;
}

export interface AuditHistoryResponse {
  patientId: string;
  entries: AuditHistoryEntry[];
}

/* ------------------------------------------------------------------ */
/*  Raw backend shapes                                                  */
/*                                                                      */
/*  These mirror the actual Pydantic models returned by the FastAPI    */
/*  backend byte-for-byte (snake_case field names, backend value        */
/*  vocab e.g. "LOW"/"MODERATE"/"HIGH"/"CRITICAL" risk levels). They    */
/*  are mapped to the camelCase UI types above in `services/audit`.     */
/*  Source: backend/models/audit.py (AuditReport, AuditSummary,        */
/*  ClaimExplanation, TimelineEvent, DecisionTrace) and                */
/*  backend/models/schemas.py (HallucinationResult, ValidationResult,  */
/*  AlertPayload).                                                      */
/* ------------------------------------------------------------------ */

/** GET /audit-history/{patient_id} returns this array directly (no wrapper). */
export interface ApiAuditSummary {
  session_id: string;
  patient_id: string;
  timestamp: string;
  risk_level?: string | null;
  risk_score?: number | null;
  hallucination_count: number;
  claim_count: number;
  passed_evaluation?: boolean | null;
}

export interface ApiHallucinationResult {
  is_hallucination: boolean;
  detected_text: string;
  confidence_score: number;
  details: string;
}

export interface ApiValidationResult {
  claim_id: string;
  claim_text?: string | null;
  is_valid: boolean;
  source: string;
  confidence: number;
  reasoning: string;
}

export interface ApiClaimExplanation {
  explanation_id: string;
  category: string;
  title: string;
  reasoning: string;
  evidence: string[];
  confidence: number;
  generated_at: string;
}

export interface ApiTimelineEvent {
  agent_name: string;
  start_time: string;
  end_time: string;
  execution_time_ms: number;
  status: string;
  actions_performed: string[];
}

export interface ApiDecisionTrace {
  decision_id: string;
  agent_name: string;
  action: string;
  evidence: string[];
  confidence: number;
  timestamp: string;
}

export interface ApiAlertPayload {
  alert_id: string;
  severity: string;
  message: string;
  timestamp: string;
}

/** GET /audit/{session_id} */
export interface ApiAuditReport {
  session_id: string;
  patient_id: string;
  timestamp: string;
  session_metadata: Record<string, unknown>;
  patient_information: Record<string, unknown>;
  medical_entities: Record<string, unknown[]>;
  hallucinations: ApiHallucinationResult[];
  validated_claims: ApiValidationResult[];
  explanations: ApiClaimExplanation[];
  risk_assessment: Record<string, unknown> & {
    risk_level?: string;
    risk_score?: number;
  };
  safe_response: string;
  evaluation_report?: Record<string, unknown> | null;
  alerts: ApiAlertPayload[];
  timeline: ApiTimelineEvent[];
  decision_trace: ApiDecisionTrace[];
  pipeline_started_at?: string | null;
  pipeline_completed_at?: string | null;
}


/* ------------------------------------------------------------------ */
/*  Detail (single report) — GET /audit/{session_id}                   */
/* ------------------------------------------------------------------ */

export type AuditTimelineEventType =
  | "input"
  | "processing"
  | "decision"
  | "validation"
  | "output"
  | "alert";

export interface AuditTimelineEvent {
  id: string;
  timestamp: string; // ISO 8601
  type: AuditTimelineEventType;
  title: string;
  description?: string;
  actor?: string;
}

export interface AuditDecisionStep {
  id: string;
  order: number;
  title: string;
  description: string;
  confidence?: number; // 0 - 1
  inputSummary?: string;
  outputSummary?: string;
  durationMs?: number;
}

export interface AuditExplanationFactor {
  name: string;
  weight: number; // 0 - 1
  description?: string;
}

export interface AuditExplanation {
  summary: string;
  reasoning: string[];
  factors: AuditExplanationFactor[];
  citations?: string[];
}

export interface HallucinationFinding {
  id: string;
  claim: string;
  severity: AuditRiskLevel;
  confidence: number; // 0 - 1
  verified: boolean;
  sourceSpan?: string;
  explanation?: string;
}

export type ValidationStatus = "passed" | "failed" | "warning";

export interface ValidationCheck {
  id: string;
  name: string;
  category: string;
  status: ValidationStatus;
  details?: string;
  ruleRef?: string;
}

// NOTE: patientName, modelName, modelVersion have no backend source (see
// AuditHistoryEntry note above) and are always undefined when mapped from
// the real API.
export interface AuditReport {
  sessionId: string;
  patientId: string;
  patientName?: string;
  createdAt: string;
  completedAt?: string;
  riskLevel: AuditRiskLevel;
  outcome: AuditOutcome;
  modelName?: string;
  modelVersion?: string;
  summary: string;
  timeline: AuditTimelineEvent[];
  decisionTrace: AuditDecisionStep[];
  explanation: AuditExplanation;
  hallucinations: HallucinationFinding[];
  validations: ValidationCheck[];
}

/* ------------------------------------------------------------------ */
/*  Filters / UI state                                                  */
/* ------------------------------------------------------------------ */

export interface AuditSearchFilters {
  patientId: string;
  sessionQuery: string;
  riskLevel: AuditRiskLevel | "all";
}

/* ------------------------------------------------------------------ */
/*  Export                                                              */
/* ------------------------------------------------------------------ */

export type AuditExportFormat = "json" | "pdf";

export interface AuditExportResult {
  blob: Blob;
  filename: string;
}

/* ------------------------------------------------------------------ */
/*  Service errors                                                      */
/* ------------------------------------------------------------------ */

export type AuditServiceErrorKind = "network" | "server" | "not_found";

export class AuditServiceError extends Error {
  kind: AuditServiceErrorKind;
  status?: number;

  constructor(message: string, kind: AuditServiceErrorKind, status?: number) {
    super(message);
    this.name = "AuditServiceError";
    this.kind = kind;
    this.status = status;
  }
}
