// Pipeline API integration for ClinGuard-AI.
//
// The Pipeline module renders the same underlying session record the
// Audit module reads, just as an agent execution graph rather than a
// decision trace. It goes through the same `GET /audit/{session_id}`
// endpoint the Audit module uses — every network call goes through
// `request()` from `api/client.ts`, the same seam every other service
// uses, so there are no hardcoded URLs here. Base path comes from an env
// var (defaulting to the documented backend route) and is read once at
// module load, mirroring `services/audit/auditApi.ts`.
//
// There is no local mock fallback: if the backend is unreachable or
// returns an error, callers receive a typed `PipelineServiceError` and
// the UI renders a real error state rather than synthesized data.

import { ApiError, request } from "../../api/client";
import type { ApiAuditReport, ApiTimelineEvent } from "../../types/audit";
import {
  PIPELINE_AGENT_ORDER,
  PipelineServiceError,
  type PipelineAgentDecision,
  type PipelineAgentId,
  type PipelineAgentNode,
  type PipelineAgentStatus,
  type PipelineExecutionReport,
  type PipelineTimelineEvent,
} from "../../types/pipeline";

const PIPELINE_SESSION_ENDPOINT =
  import.meta.env.VITE_PIPELINE_SESSION_ENDPOINT ?? "/audit";

/** Maps a backend "XxxAgent" name (e.g. "InterceptorAgent") to the
 * fixed pipeline agent id (e.g. "interceptor"). */
function agentNameToId(agentName: string): PipelineAgentId | null {
  const normalized = agentName.replace(/Agent$/i, "").toLowerCase();
  return (PIPELINE_AGENT_ORDER as string[]).includes(normalized)
    ? (normalized as PipelineAgentId)
    : null;
}

function mapAgentStatus(status: string): PipelineAgentStatus {
  return status.toUpperCase() === "SUCCESS" ? "completed" : "failed";
}

/** Maps a completed `GET /audit/{session_id}` response into the 8-stage
 * agent execution graph the Pipeline module renders. Agents with no
 * matching timeline entry (the pipeline hadn't reached them, or failed
 * earlier) are reported as "pending" rather than invented as complete. */
function mapAuditReportToPipeline(
  report: ApiAuditReport
): PipelineExecutionReport {
  const eventsByAgent = new Map<PipelineAgentId, ApiTimelineEvent>();
  for (const event of report.timeline) {
    const id = agentNameToId(event.agent_name);
    if (id) eventsByAgent.set(id, event);
  }

  const decisionsByAgent = new Map<PipelineAgentId, PipelineAgentDecision[]>();
  for (const decision of report.decision_trace) {
    const id = agentNameToId(decision.agent_name);
    if (!id) continue;
    const list = decisionsByAgent.get(id) ?? [];
    list.push({
      id: decision.decision_id,
      description: decision.action,
      rationale:
        decision.evidence.length > 0 ? decision.evidence.join("; ") : undefined,
      confidence: decision.confidence,
    });
    decisionsByAgent.set(id, list);
  }

  const agents: PipelineAgentNode[] = PIPELINE_AGENT_ORDER.map((agentId) => {
    const event = eventsByAgent.get(agentId);
    if (!event) {
      return {
        id: agentId,
        status: "pending" as PipelineAgentStatus,
        actions: [],
        evidence: [],
        decisions: decisionsByAgent.get(agentId) ?? [],
      };
    }
    return {
      id: agentId,
      status: mapAgentStatus(event.status),
      startedAt: event.start_time,
      completedAt: event.end_time,
      durationMs: event.execution_time_ms,
      actions: event.actions_performed.map((action, index) => ({
        id: `${report.session_id}-${agentId}-action-${index}`,
        label: action,
        timestamp: event.start_time,
      })),
      evidence: [],
      decisions: decisionsByAgent.get(agentId) ?? [],
    };
  });

  const timeline: PipelineTimelineEvent[] = report.timeline.map(
    (event, index) => {
      const agentId = agentNameToId(event.agent_name);
      return {
        id: `${report.session_id}-timeline-${index}`,
        timestamp: event.start_time,
        type:
          event.status.toUpperCase() === "SUCCESS"
            ? "agent_completed"
            : "agent_failed",
        agentId: agentId ?? undefined,
        title: `${event.agent_name} ${
          event.status.toUpperCase() === "SUCCESS" ? "completed" : "failed"
        }`,
        description:
          event.actions_performed.length > 0
            ? event.actions_performed.join("; ")
            : undefined,
      };
    }
  );

  const allSucceeded = report.timeline.every(
    (e) => e.status.toUpperCase() === "SUCCESS"
  );
  const anyFailed = report.timeline.some(
    (e) => e.status.toUpperCase() !== "SUCCESS"
  );
  const status = anyFailed ? "failed" : allSucceeded ? "completed" : "running";

  const totalLatencyMs = report.timeline.reduce(
    (sum, e) => sum + e.execution_time_ms,
    0
  );

  return {
    sessionId: report.session_id,
    patientId: report.patient_id,
    status,
    startedAt: report.pipeline_started_at ?? report.timestamp,
    completedAt: report.pipeline_completed_at ?? undefined,
    totalLatencyMs: totalLatencyMs || undefined,
    summary: `${report.hallucinations.filter((h) => h.is_hallucination).length} hallucination(s), risk level ${
      report.risk_assessment.risk_level ?? "unknown"
    }`,
    agents,
    timeline,
  };
}

function toServiceError(
  error: unknown,
  notFoundMessage: string
): PipelineServiceError {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return new PipelineServiceError(
        notFoundMessage,
        "not_found",
        error.status
      );
    }
    return new PipelineServiceError(
      error.status >= 500
        ? "The pipeline service is temporarily unavailable. Please try again."
        : "The pipeline service could not process that request.",
      "server",
      error.status
    );
  }

  return new PipelineServiceError(
    "Unable to reach the pipeline service. Check your connection and try again.",
    "network"
  );
}

/**
 * Fetches the pipeline execution report for a single session.
 * Corresponds to `GET /audit/{session_id}`.
 */
export async function getPipelineExecutionBySessionId(
  sessionId: string,
  signal?: AbortSignal
): Promise<PipelineExecutionReport> {
  try {
    const raw = await request<ApiAuditReport>(
      `${PIPELINE_SESSION_ENDPOINT}/${encodeURIComponent(sessionId)}`,
      { signal }
    );
    return mapAuditReportToPipeline(raw);
  } catch (error) {

    throw toServiceError(
      error,
      `No pipeline execution was found for session "${sessionId}".`
    );
  }
}
