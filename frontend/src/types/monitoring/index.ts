// Domain types for the Monitoring module.
//
// Models live system/model health and rolling metrics for the monitoring
// dashboard: KPI overview, risk/hallucination/validation trends, request
// volume, per-agent performance, and component health checks.

import type { KpiStat, ModelStatus } from "../index";

/** Health status vocabulary. Reuses the shared `ModelStatus` scale so the
 * existing `modelStatusToBadgeColor` mapping applies to health cards and
 * the agent performance table. */
export type HealthStatus = ModelStatus;

export type MonitoringTimeRange = "24h" | "7d" | "30d";

/* ------------------------------------------------------------------ */
/*  Raw backend shapes                                                  */
/*                                                                      */
/*  The backend has no server-side time-range filtering - every         */
/*  /metrics/* endpoint (except /overview and /agents) returns the      */
/*  full hourly/daily/weekly/monthly breakdown every time. The service  */
/*  layer picks the right bucket granularity and trims it client-side   */
/*  to approximate a MonitoringTimeRange selection.                     */
/*  Source: backend/services/metrics_aggregator.py, agent_metrics_service.py,*/
/*  analytics_service.py, system_health_service.py.                     */
/* ------------------------------------------------------------------ */

export interface ApiMetricsOverview {
  total_requests: number;
  average_latency_ms: number;
  average_risk_score: number;
  hallucination_rate: number;
  validation_success_rate: number;
  alerts_generated: number;
  high_risk_cases: number;
  average_pipeline_execution_time_ms: number;
}

export interface ApiPeriodStats {
  count: number;
  avg_risk_score: number | null;
  min_risk_score: number | null;
  max_risk_score: number | null;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  hallucination_rate: number | null;
  validation_success_rate: number | null;
  total_alerts: number;
  high_risk_cases: number;
  avg_pipeline_time_ms: number | null;
  rolling_avg_risk?: number | null;
  trend?: string;
}

export interface ApiBucketedStats {
  hourly: Record<string, ApiPeriodStats>;
  daily: Record<string, ApiPeriodStats>;
  weekly: Record<string, ApiPeriodStats>;
  monthly: Record<string, ApiPeriodStats>;
}

/** GET /metrics/risk-trends */
export type ApiRiskTrendsResponse = ApiBucketedStats;

/** GET /metrics/hallucinations, /metrics/validations, /metrics/performance */
export interface ApiPeriodBreakdownResponse extends ApiBucketedStats {
  summary: ApiPeriodStats;
  trend: string;
}

export interface ApiAgentMetrics {
  agent_name: string;
  execution_count: number;
  success_count: number;
  failure_count: number;
  total_execution_time_ms: number;
  minimum_latency_ms: number;
  maximum_latency_ms: number;
  last_execution_time: string | null;
  success_rate: number;
  failure_rate: number;
  average_latency_ms: number;
}

/** GET /metrics/agents */
export interface ApiAgentsResponse {
  agents: Record<string, ApiAgentMetrics>;
}

export type ApiHealthStatus = "healthy" | "degraded" | "unhealthy" | "unknown";

/** GET /health/pipeline, /health/storage, /health/models, /health/system */
export interface ApiComponentHealth {
  component: string;
  status: ApiHealthStatus;
  timestamp: string;
  details: Record<string, unknown>;
  errors: string[];
  recommendations: string[];
}

/**
 * GET /health - NOTE: the backend registers two competing handlers for
 * this exact path (backend/api/endpoints.py's simple handler, and
 * backend/routers/health_router.py's full SystemHealthReport handler).
 * Because endpoints.py's router is included first in main.py, its
 * simple handler wins and the richer report is unreachable. This is
 * what the real server returns for `GET /health` today.
 */
export interface ApiSimpleHealth {
  status: string;
  service: string;
  version: string;
}


/* ------------------------------------------------------------------ */
/*  GET /metrics/overview                                              */
/* ------------------------------------------------------------------ */

export interface MetricsOverviewResponse {
  kpis: KpiStat[];
}

/* ------------------------------------------------------------------ */
/*  GET /metrics/risk-trends                                           */
/* ------------------------------------------------------------------ */

export interface RiskTrendPoint {
  label: string;
  riskScore: number;
  incidentCount: number;
}

/* ------------------------------------------------------------------ */
/*  GET /metrics/hallucinations                                        */
/* ------------------------------------------------------------------ */

export interface HallucinationTrendPoint {
  label: string;
  count: number;
  ratePct: number;
}

/* ------------------------------------------------------------------ */
/*  GET /metrics/validations                                           */
/* ------------------------------------------------------------------ */

export interface ValidationTrendPoint {
  label: string;
  passRatePct: number;
  failCount: number;
}

/* ------------------------------------------------------------------ */
/*  GET /metrics/performance                                           */
/* ------------------------------------------------------------------ */

export interface RequestVolumePoint {
  label: string;
  requests: number;
  avgLatencyMs: number;
  errorRatePct: number;
}

/* ------------------------------------------------------------------ */
/*  GET /metrics/agents                                                */
/* ------------------------------------------------------------------ */

// NOTE: the backend's AgentMetrics dataclass tracks execution/success/
// failure counts and latency per agent, but has no per-agent hallucination
// rate (that's only tracked platform-wide via /metrics/overview) - left
// optional and always undefined when populated from the real API.
export interface AgentPerformanceEntry {
  id: string;
  agentName: string;
  status: HealthStatus;
  requestsHandled: number;
  avgLatencyMs: number;
  successRatePct: number;
  hallucinationRatePct?: number;
  lastActiveAt: string; // ISO 8601
}

/* ------------------------------------------------------------------ */
/*  GET /health, /health/pipeline, /health/storage, /health/models     */
/* ------------------------------------------------------------------ */

export interface ComponentHealth {
  status: HealthStatus;
  message?: string;
  latencyMs?: number;
  uptimePct?: number;
  lastCheckedAt: string; // ISO 8601
}

export interface SystemHealthSnapshot {
  overall: ComponentHealth;
  pipeline: ComponentHealth;
  storage: ComponentHealth;
  models: ComponentHealth;
}

/* ------------------------------------------------------------------ */
/*  Combined snapshot consumed by the Monitoring page                  */
/* ------------------------------------------------------------------ */

export interface MonitoringSnapshot {
  kpis: KpiStat[];
  riskTrends: RiskTrendPoint[];
  hallucinationTrends: HallucinationTrendPoint[];
  validationTrends: ValidationTrendPoint[];
  requestVolume: RequestVolumePoint[];
  agents: AgentPerformanceEntry[];
  health: SystemHealthSnapshot;
  fetchedAt: string; // ISO 8601, set client-side on successful fetch
}

/* ------------------------------------------------------------------ */
/*  Filters / UI state                                                  */
/* ------------------------------------------------------------------ */

export interface MonitoringFiltersState {
  timeRange: MonitoringTimeRange;
  agentQuery: string;
}

/* ------------------------------------------------------------------ */
/*  Service errors                                                      */
/* ------------------------------------------------------------------ */

export type MonitoringServiceErrorKind = "network" | "server";

export class MonitoringServiceError extends Error {
  kind: MonitoringServiceErrorKind;
  status?: number;

  constructor(
    message: string,
    kind: MonitoringServiceErrorKind,
    status?: number
  ) {
    super(message);
    this.name = "MonitoringServiceError";
    this.kind = kind;
    this.status = status;
  }
}
