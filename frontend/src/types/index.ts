// Shared domain types for ClinGuard-AI.
// These model the data returned by the (future) backend API. Until that
// backend exists, the `services/` layer returns mock data that conforms
// to these same shapes, so swapping in real API calls later requires no
// changes to components.

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type TrendDirection = "up" | "down" | "neutral";

export interface KpiStat {
  id: string;
  label: string;
  value: string;
  unit?: string;
  change?: string;
  trend?: TrendDirection;
  helpText?: string;
}

/* ------------------------------------------------------------------ */
/*  Audit                                                              */
/* ------------------------------------------------------------------ */

export type AuditActionType =
  | "login"
  | "access"
  | "model_inference"
  | "data_export"
  | "data_modification"
  | "deletion"
  | "config_change";

export type AuditStatus = "success" | "failed" | "flagged";

export interface AuditLogEntry {
  id: string;
  timestamp: string; // ISO 8601
  actor: string;
  actorRole: string;
  actionType: AuditActionType;
  action: string;
  resource: string;
  ipAddress: string;
  status: AuditStatus;
  severity: Severity;
  details?: string;
}

export interface AuditFilters {
  query?: string;
  status?: AuditStatus | "all";
  severity?: Severity | "all";
}

/* ------------------------------------------------------------------ */
/*  Monitoring                                                         */
/* ------------------------------------------------------------------ */

export type ModelStatus = "healthy" | "degraded" | "offline";

export interface ModelHealth {
  id: string;
  name: string;
  version: string;
  status: ModelStatus;
  uptimePct: number;
  latencyMs: number;
  driftScore: number; // 0 - 1, higher = more drift from baseline
  requestsPerMin: number;
  lastCheckedAt: string;
}

export interface MonitoringAlert {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  severity: Severity;
  source: string;
  acknowledged: boolean;
}

export interface LatencyPoint {
  label: string;
  latencyMs: number;
  errorRatePct: number;
}

/* ------------------------------------------------------------------ */
/*  Pipeline                                                            */
/* ------------------------------------------------------------------ */

export type PipelineStageStatus =
  | "completed"
  | "running"
  | "pending"
  | "failed"
  | "skipped";

export interface PipelineStage {
  id: string;
  name: string;
  status: PipelineStageStatus;
  durationSec?: number;
}

export type PipelineRunStatus =
  | "completed"
  | "running"
  | "failed"
  | "queued";

export interface PipelineRun {
  id: string;
  pipelineName: string;
  status: PipelineRunStatus;
  progressPct: number;
  startedAt: string;
  completedAt?: string;
  triggeredBy: string;
  datasetVersion: string;
  stages: PipelineStage[];
}

/* ------------------------------------------------------------------ */
/*  Dashboard                                                           */
/* ------------------------------------------------------------------ */

export interface ComplianceTrendPoint {
  label: string;
  complianceScore: number;
  incidents: number;
}

export interface SeverityBreakdownPoint {
  severity: Severity;
  count: number;
}

export interface DashboardSummary {
  kpis: KpiStat[];
  complianceTrend: ComplianceTrendPoint[];
  severityBreakdown: SeverityBreakdownPoint[];
  recentAuditEntries: AuditLogEntry[];
  activeAlerts: MonitoringAlert[];
  activePipelineRuns: PipelineRun[];
}
