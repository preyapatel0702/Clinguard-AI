// Audit API integration for ClinGuard-AI.
//
// Every network call goes through `request()` / `requestBlob()` from
// `api/client.ts` — the same seam every other service uses — so there are
// no hardcoded URLs here. Base paths come from env vars (with sane
// defaults matching the documented backend routes) and are read once at
// module load, mirroring `services/chat/chatApi.ts`.
//
// There is no local mock fallback: if the backend is unreachable or
// returns an error, callers receive a typed `AuditServiceError` and the
// UI renders a real error state rather than synthesized data.

import { ApiError, request, requestBlob } from "../../api/client";
import {
  AuditServiceError,
  type ApiAuditReport,
  type ApiAuditSummary,
  type AuditDecisionStep,
  type AuditExplanation,
  type AuditExportFormat,
  type AuditExportResult,
  type AuditHistoryEntry,
  type AuditHistoryResponse,
  type AuditOutcome,
  type AuditReport,
  type AuditRiskLevel,
  type AuditTimelineEvent,
  type AuditTimelineEventType,
  type HallucinationFinding,
  type ValidationCheck,
} from "../../types/audit";

const AUDIT_SESSION_ENDPOINT =
  import.meta.env.VITE_AUDIT_SESSION_ENDPOINT ?? "/audit";

const AUDIT_HISTORY_ENDPOINT =
  import.meta.env.VITE_AUDIT_HISTORY_ENDPOINT ?? "/audit-history";

/* ------------------------------------------------------------------ */
/*  Backend -> UI mapping                                               */
/*                                                                      */
/*  The backend's risk vocabulary is upper-case (LOW/MODERATE/HIGH/     */
/*  CRITICAL); the UI's Severity scale is lower-case and uses "medium"  */
/*  instead of "moderate". `passed_evaluation` is the closest backend   */
/*  concept to an "outcome" - there is no approve/reject workflow in    */
/*  the backend, so this mapping is a best-effort derivation, not a     */
/*  real outcome field returned by the API.                             */
/* ------------------------------------------------------------------ */

function mapRiskLevel(level: string | null | undefined): AuditRiskLevel {
  switch ((level ?? "").toUpperCase()) {
    case "CRITICAL":
      return "critical";
    case "HIGH":
      return "high";
    case "MODERATE":
    case "MEDIUM":
      return "medium";
    case "LOW":
      return "low";
    default:
      return "info";
  }
}

function mapOutcome(passedEvaluation: boolean | null | undefined): AuditOutcome {
  if (passedEvaluation === true) return "approved";
  if (passedEvaluation === false) return "flagged";
  return "pending_review";
}

function mapAgentToTimelineType(agentName: string): AuditTimelineEventType {
  const normalized = agentName.replace(/Agent$/i, "").toLowerCase();
  switch (normalized) {
    case "interceptor":
      return "input";
    case "detector":
    case "memory":
      return "processing";
    case "validator":
      return "validation";
    case "risk":
    case "evaluator":
      return "decision";
    case "generator":
      return "output";
    case "alert":
      return "alert";
    default:
      return "processing";
  }
}

function mapConfidenceToSeverity(confidence: number): AuditRiskLevel {
  if (confidence >= 0.85) return "critical";
  if (confidence >= 0.65) return "high";
  if (confidence >= 0.4) return "medium";
  if (confidence > 0) return "low";
  return "info";
}

function toServiceError(error: unknown, notFoundMessage: string): AuditServiceError {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return new AuditServiceError(notFoundMessage, "not_found", error.status);
    }
    return new AuditServiceError(
      error.status >= 500
        ? "The audit service is temporarily unavailable. Please try again."
        : "The audit service could not process that request.",
      "server",
      error.status
    );
  }

  return new AuditServiceError(
    "Unable to reach the audit service. Check your connection and try again.",
    "network"
  );
}

function summaryFromReport(report: ApiAuditReport): string {
  const hallucinationCount = report.hallucinations.filter(
    (h) => h.is_hallucination
  ).length;
  const riskLevel = report.risk_assessment.risk_level ?? "UNKNOWN";
  return `Risk: ${riskLevel} · ${hallucinationCount} hallucination${
    hallucinationCount === 1 ? "" : "s"
  } detected · ${report.validated_claims.length} claim${
    report.validated_claims.length === 1 ? "" : "s"
  } validated`;
}

/** Maps a raw `GET /audit-history/{patient_id}` list item to the UI shape. */
export function mapAuditSummary(summary: ApiAuditSummary): AuditHistoryEntry {
  return {
    sessionId: summary.session_id,
    patientId: summary.patient_id,
    createdAt: summary.timestamp,
    riskLevel: mapRiskLevel(summary.risk_level),
    outcome: mapOutcome(summary.passed_evaluation),
    summary: `Risk score ${
      summary.risk_score != null ? summary.risk_score.toFixed(2) : "n/a"
    } · ${summary.hallucination_count} hallucination${
      summary.hallucination_count === 1 ? "" : "s"
    } · ${summary.claim_count} claim${summary.claim_count === 1 ? "" : "s"}`,
    hallucinationCount: summary.hallucination_count,
    validationFailureCount: summary.claim_count,
  };
}

/** Maps a raw `GET /audit/{session_id}` response to the UI shape. */
export function mapAuditReport(report: ApiAuditReport): AuditReport {
  const timeline: AuditTimelineEvent[] = report.timeline.map((event, index) => ({
    id: `${report.session_id}-timeline-${index}`,
    timestamp: event.start_time,
    type: mapAgentToTimelineType(event.agent_name),
    title: event.agent_name,
    description:
      event.actions_performed.length > 0
        ? event.actions_performed.join("; ")
        : undefined,
    actor: event.agent_name,
  }));

  const decisionTrace: AuditDecisionStep[] = report.decision_trace.map(
    (decision, index) => ({
      id: decision.decision_id,
      order: index + 1,
      title: decision.action,
      description:
        decision.evidence.length > 0
          ? decision.evidence.join("; ")
          : decision.agent_name,
      confidence: decision.confidence,
      outputSummary: decision.agent_name,
    })
  );

  const explanation: AuditExplanation = {
    summary:
      report.explanations.length > 0
        ? report.explanations[0].title
        : "No explanation was generated for this session.",
    reasoning: report.explanations.map((e) => e.reasoning),
    factors: report.explanations.map((e) => ({
      name: e.title,
      weight: e.confidence,
      description: e.category,
    })),
    citations: report.explanations.flatMap((e) => e.evidence),
  };

  const hallucinations: HallucinationFinding[] = report.hallucinations.map(
    (h, index) => ({
      id: `${report.session_id}-hallucination-${index}`,
      claim: h.detected_text,
      severity: mapConfidenceToSeverity(h.confidence_score),
      confidence: h.confidence_score,
      verified: !h.is_hallucination,
      explanation: h.details,
    })
  );

  const validations: ValidationCheck[] = report.validated_claims.map(
    (v, index) => ({
      id: v.claim_id || `${report.session_id}-validation-${index}`,
      name: v.claim_text ?? v.claim_id,
      category: v.source,
      status: v.is_valid ? "passed" : "failed",
      details: v.reasoning || undefined,
    })
  );

  return {
    sessionId: report.session_id,
    patientId: report.patient_id,
    createdAt: report.timestamp,
    completedAt: report.pipeline_completed_at ?? undefined,
    riskLevel: mapRiskLevel(report.risk_assessment.risk_level),
    outcome: mapOutcome(
      (report.evaluation_report as { passed?: boolean } | null | undefined)
        ?.passed
    ),
    summary: summaryFromReport(report),
    timeline,
    decisionTrace,
    explanation,
    hallucinations,
    validations,
  };
}

/**
 * Fetches the full audit report for a single session.
 * Corresponds to `GET /audit/{session_id}`.
 */
export async function getAuditBySessionId(
  sessionId: string,
  signal?: AbortSignal
): Promise<AuditReport> {
  try {
    const raw = await request<ApiAuditReport>(
      `${AUDIT_SESSION_ENDPOINT}/${encodeURIComponent(sessionId)}`,
      { signal }
    );
    return mapAuditReport(raw);
  } catch (error) {
    throw toServiceError(
      error,
      `No audit report was found for session "${sessionId}".`
    );
  }
}

/**
 * Fetches the audit history (list of prior sessions) for a patient.
 * Corresponds to `GET /audit-history/{patient_id}`.
 */
export async function getAuditHistoryByPatientId(
  patientId: string,
  signal?: AbortSignal
): Promise<AuditHistoryResponse> {
  try {
    // The backend returns a raw JSON array of AuditSummary objects, not a
    // { patientId, entries } wrapper - the wrapper shape is reconstructed
    // here so existing components don't need to change.
    const raw = await request<ApiAuditSummary[]>(
      `${AUDIT_HISTORY_ENDPOINT}/${encodeURIComponent(patientId)}`,
      { signal }
    );
    return {
      patientId,
      entries: raw.map(mapAuditSummary),
    };
  } catch (error) {
    throw toServiceError(
      error,
      `No audit history was found for patient "${patientId}".`
    );
  }
}

/**
 * Deletes a session's audit report. Corresponds to `DELETE /audit/{session_id}`.
 * Not currently wired to any UI action (none exists in the audit
 * components), but exposed here since the backend supports it.
 */
export async function deleteAudit(
  sessionId: string,
  signal?: AbortSignal
): Promise<boolean> {
  try {
    const result = await request<{ deleted: boolean }>(
      `${AUDIT_SESSION_ENDPOINT}/${encodeURIComponent(sessionId)}`,
      { method: "DELETE", signal }
    );
    return result.deleted;
  } catch (error) {
    throw toServiceError(
      error,
      `No audit report was found for session "${sessionId}".`
    );
  }
}

function extensionFor(format: AuditExportFormat): string {
  return format === "json" ? "json" : "pdf";
}

/**
 * Downloads the export for a session in the given format.
 * Corresponds to `GET /audit/{session_id}/export/json` and
 * `GET /audit/{session_id}/export/pdf`.
 */
export async function exportAudit(
  sessionId: string,
  format: AuditExportFormat,
  signal?: AbortSignal
): Promise<AuditExportResult> {
  try {
    const { blob, filename } = await requestBlob(
      `${AUDIT_SESSION_ENDPOINT}/${encodeURIComponent(sessionId)}/export/${format}`,
      { signal }
    );

    return {
      blob,
      filename: filename ?? `audit-${sessionId}.${extensionFor(format)}`,
    };
  } catch (error) {
    throw toServiceError(
      error,
      `No exportable audit report was found for session "${sessionId}".`
    );
  }
}

/** Triggers a browser download for an export result. */
export function saveExportToDisk(result: AuditExportResult): void {
  const url = URL.createObjectURL(result.blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = result.filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
