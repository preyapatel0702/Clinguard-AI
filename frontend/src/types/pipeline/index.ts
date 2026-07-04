// Domain types for the Pipeline module.
//
// Models the 8-stage clinical AI governance pipeline that every session
// runs through: Interceptor -> Detector -> Validator -> Risk ->
// Generator -> Evaluator -> Memory -> Alert. This is a different view of
// the same underlying session record `AuditReport` covers — where the
// Audit module presents a session as a decision trace, explanation, and
// findings, the Pipeline module presents the same session as a live
// agent-by-agent execution graph. Both are served by `GET /audit/{session_id}`.

import type { PipelineRunStatus } from "../index";

/** The eight fixed agents every pipeline execution passes through. */
export type PipelineAgentId =
  | "interceptor"
  | "detector"
  | "validator"
  | "risk"
  | "generator"
  | "evaluator"
  | "memory"
  | "alert";

export const PIPELINE_AGENT_ORDER: PipelineAgentId[] = [
  "interceptor",
  "detector",
  "validator",
  "risk",
  "generator",
  "evaluator",
  "memory",
  "alert",
];

export const PIPELINE_AGENT_LABELS: Record<PipelineAgentId, string> = {
  interceptor: "Interceptor",
  detector: "Detector",
  validator: "Validator",
  risk: "Risk",
  generator: "Generator",
  evaluator: "Evaluator",
  memory: "Memory",
  alert: "Alert",
};

export const PIPELINE_AGENT_DESCRIPTIONS: Record<PipelineAgentId, string> = {
  interceptor: "Captures and normalizes the incoming request.",
  detector: "Scans for PHI, prompt injection, and unsafe input patterns.",
  validator: "Checks the request against clinical and policy guardrails.",
  risk: "Scores the request and candidate response for clinical risk.",
  generator: "Produces the candidate model response.",
  evaluator: "Evaluates the response for hallucination and correctness.",
  memory: "Persists session context and precedent for future runs.",
  alert: "Raises alerts and routes for human review when required.",
};

export type PipelineAgentStatus =
  | "completed"
  | "running"
  | "pending"
  | "failed"
  | "skipped";

/** A single action an agent took during execution (e.g. a rule fired, a
 * tool call made, a policy applied). */
export interface PipelineAgentAction {
  id: string;
  label: string;
  timestamp: string; // ISO 8601
  detail?: string;
}

/** A piece of evidence an agent gathered or relied on (e.g. a matched
 * pattern, a retrieved record, a source citation). */
export interface PipelineAgentEvidence {
  id: string;
  label: string;
  value: string;
  source?: string;
}

/** A decision an agent made, optionally with the confidence behind it. */
export interface PipelineAgentDecision {
  id: string;
  description: string;
  rationale?: string;
  confidence?: number; // 0 - 1
}

export interface PipelineAgentNode {
  id: PipelineAgentId;
  status: PipelineAgentStatus;
  startedAt?: string; // ISO 8601
  completedAt?: string; // ISO 8601
  durationMs?: number;
  confidence?: number; // 0 - 1
  summary?: string;
  actions: PipelineAgentAction[];
  evidence: PipelineAgentEvidence[];
  decisions: PipelineAgentDecision[];
}

export type PipelineTimelineEventType =
  | "started"
  | "agent_started"
  | "agent_completed"
  | "agent_failed"
  | "alert_raised"
  | "completed";

export interface PipelineTimelineEvent {
  id: string;
  timestamp: string; // ISO 8601
  type: PipelineTimelineEventType;
  agentId?: PipelineAgentId;
  title: string;
  description?: string;
}

/** Full execution report for one pipeline session — the shape returned
 * by `GET /audit/{session_id}` as consumed by the Pipeline module. */
export interface PipelineExecutionReport {
  sessionId: string;
  patientId?: string;
  patientName?: string;
  status: PipelineRunStatus;
  startedAt: string; // ISO 8601
  completedAt?: string; // ISO 8601
  totalLatencyMs?: number;
  modelName?: string;
  summary?: string;
  agents: PipelineAgentNode[];
  timeline: PipelineTimelineEvent[];
}

/* ------------------------------------------------------------------ */
/*  Service errors                                                      */
/* ------------------------------------------------------------------ */

export type PipelineServiceErrorKind = "network" | "server" | "not_found";

export class PipelineServiceError extends Error {
  kind: PipelineServiceErrorKind;
  status?: number;

  constructor(
    message: string,
    kind: PipelineServiceErrorKind,
    status?: number
  ) {
    super(message);
    this.name = "PipelineServiceError";
    this.kind = kind;
    this.status = status;
  }
}
