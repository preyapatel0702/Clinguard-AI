// Monitoring API integration for ClinGuard-AI.
//
// Every network call goes through `request()` from `api/client.ts` — the
// same seam every other service uses — so there are no hardcoded URLs
// here. Base paths come from env vars (with defaults matching the
// documented backend routes) and are read once at module load, mirroring
// `services/audit/auditApi.ts`.
//
// There is no local mock fallback: if the backend is unreachable or
// returns an error, callers receive a typed `MonitoringServiceError` and
// the UI renders a real error state rather than synthesized data.

import { ApiError, request } from "../../api/client";
import type { KpiStat } from "../../types";
import {
  MonitoringServiceError,
  type AgentPerformanceEntry,
  type ApiAgentMetrics,
  type ApiAgentsResponse,
  type ApiComponentHealth,
  type ApiHealthStatus,
  type ApiMetricsOverview,
  type ApiPeriodBreakdownResponse,
  type ApiPeriodStats,
  type ApiRiskTrendsResponse,
  type ApiSimpleHealth,
  type ComponentHealth,
  type HallucinationTrendPoint,
  type HealthStatus,
  type MetricsOverviewResponse,
  type MonitoringSnapshot,
  type MonitoringTimeRange,
  type RequestVolumePoint,
  type RiskTrendPoint,
  type ValidationTrendPoint,
} from "../../types/monitoring";

const METRICS_ENDPOINT = import.meta.env.VITE_METRICS_ENDPOINT ?? "/metrics";

const HEALTH_ENDPOINT = import.meta.env.VITE_HEALTH_ENDPOINT ?? "/health";

function toServiceError(error: unknown): MonitoringServiceError {
  if (error instanceof ApiError) {
    return new MonitoringServiceError(
      error.status >= 500
        ? "The monitoring service is temporarily unavailable. Please try again."
        : "The monitoring service could not process that request.",
      "server",
      error.status
    );
  }

  return new MonitoringServiceError(
    "Unable to reach the monitoring service. Check your connection and try again.",
    "network"
  );
}

/** Picks the bucket granularity + item count that best approximates a
 * MonitoringTimeRange, since the backend always returns every bucket. */
function bucketFor(range: MonitoringTimeRange): {
  granularity: "hourly" | "daily";
  take: number;
} {
  switch (range) {
    case "24h":
      return { granularity: "hourly", take: 24 };
    case "7d":
      return { granularity: "daily", take: 7 };
    case "30d":
    default:
      return { granularity: "daily", take: 30 };
  }
}

function recentEntries(
  buckets: Record<string, ApiPeriodStats>,
  range: MonitoringTimeRange
): Array<[string, ApiPeriodStats]> {
  const { take } = bucketFor(range);
  return Object.entries(buckets)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-take);
}

function mapHealthStatus(status: ApiHealthStatus | string): HealthStatus {
  switch (status) {
    case "healthy":
      return "healthy";
    case "degraded":
      return "degraded";
    case "unhealthy":
    case "unknown":
    default:
      return "offline";
  }
}

function mapComponentHealth(raw: ApiComponentHealth): ComponentHealth {
  return {
    status: mapHealthStatus(raw.status),
    message: raw.errors.length > 0 ? raw.errors.join("; ") : undefined,
    lastCheckedAt: raw.timestamp,
  };
}


/** Fetches KPI overview metrics. Corresponds to `GET /metrics/overview`.
 * The backend has no time-range filtering on this endpoint - it always
 * returns all-time aggregate counters, so `range` has no effect here. */
export async function getMetricsOverview(
  range: MonitoringTimeRange,
  signal?: AbortSignal
): Promise<MetricsOverviewResponse> {
  void range;
  const raw = await request<ApiMetricsOverview>(
    `${METRICS_ENDPOINT}/overview`,
    { signal }
  );

  const kpis: KpiStat[] = [
    {
      id: "total-requests",
      label: "Total Requests",
      value: raw.total_requests.toLocaleString(),
    },
    {
      id: "average-risk-score",
      label: "Average Risk Score",
      value: raw.average_risk_score.toFixed(3),
    },
    {
      id: "hallucination-rate",
      label: "Hallucination Rate",
      value: `${(raw.hallucination_rate * 100).toFixed(1)}%`,
    },
    {
      id: "validation-success-rate",
      label: "Validation Success Rate",
      value: `${(raw.validation_success_rate * 100).toFixed(1)}%`,
    },
    {
      id: "high-risk-cases",
      label: "High-Risk Cases",
      value: raw.high_risk_cases.toLocaleString(),
    },
    {
      id: "average-latency",
      label: "Average Latency",
      value: `${raw.average_latency_ms.toFixed(0)} ms`,
    },
  ];

  return { kpis };
}

/** Fetches risk trend metrics. Corresponds to `GET /metrics/risk-trends`. */
export async function getRiskTrends(
  range: MonitoringTimeRange,
  signal?: AbortSignal
): Promise<RiskTrendPoint[]> {
  const raw = await request<ApiRiskTrendsResponse>(
    `${METRICS_ENDPOINT}/risk-trends`,
    { signal }
  );
  const { granularity } = bucketFor(range);
  const buckets = raw[granularity];
  return recentEntries(buckets, range).map(([label, stats]) => ({
    label,
    riskScore: stats.avg_risk_score ?? 0,
    incidentCount: stats.high_risk_cases,
  }));
}

/** Fetches hallucination trend metrics. Corresponds to `GET /metrics/hallucinations`. */
export async function getHallucinationTrends(
  range: MonitoringTimeRange,
  signal?: AbortSignal
): Promise<HallucinationTrendPoint[]> {
  const raw = await request<ApiPeriodBreakdownResponse>(
    `${METRICS_ENDPOINT}/hallucinations`,
    { signal }
  );
  const { granularity } = bucketFor(range);
  const buckets = raw[granularity];
  return recentEntries(buckets, range).map(([label, stats]) => ({
    label,
    count: stats.count,
    ratePct: (stats.hallucination_rate ?? 0) * 100,
  }));
}

/** Fetches validation accuracy trend metrics. Corresponds to `GET /metrics/validations`. */
export async function getValidationTrends(
  range: MonitoringTimeRange,
  signal?: AbortSignal
): Promise<ValidationTrendPoint[]> {
  const raw = await request<ApiPeriodBreakdownResponse>(
    `${METRICS_ENDPOINT}/validations`,
    { signal }
  );
  const { granularity } = bucketFor(range);
  const buckets = raw[granularity];
  return recentEntries(buckets, range).map(([label, stats]) => ({
    label,
    passRatePct: (stats.validation_success_rate ?? 0) * 100,
    failCount: Math.round(
      stats.count * (1 - (stats.validation_success_rate ?? 0))
    ),
  }));
}

/** Fetches request volume / latency metrics. Corresponds to `GET /metrics/performance`. */
export async function getPerformanceMetrics(
  range: MonitoringTimeRange,
  signal?: AbortSignal
): Promise<RequestVolumePoint[]> {
  const raw = await request<ApiPeriodBreakdownResponse>(
    `${METRICS_ENDPOINT}/performance`,
    { signal }
  );
  const { granularity } = bucketFor(range);
  const buckets = raw[granularity];
  return recentEntries(buckets, range).map(([label, stats]) => ({
    label,
    requests: stats.count,
    avgLatencyMs: stats.avg_latency_ms ?? 0,
    // The backend does not track request-level error rates in this
    // breakdown (only hallucination/validation rates) - there is no
    // source field for this, so it is always 0.
    errorRatePct: 0,
  }));
}

function mapAgentMetrics(agent: ApiAgentMetrics): AgentPerformanceEntry {
  return {
    id: agent.agent_name,
    agentName: agent.agent_name,
    status: agent.success_rate >= 0.5 || agent.execution_count === 0
      ? "healthy"
      : "degraded",
    requestsHandled: agent.execution_count,
    avgLatencyMs: agent.average_latency_ms,
    successRatePct: agent.success_rate * 100,
    lastActiveAt: agent.last_execution_time ?? new Date(0).toISOString(),
  };
}

/** Fetches per-agent performance metrics. Corresponds to `GET /metrics/agents`. */
export async function getAgentPerformance(
  signal?: AbortSignal
): Promise<AgentPerformanceEntry[]> {
  const raw = await request<ApiAgentsResponse>(`${METRICS_ENDPOINT}/agents`, {
    signal,
  });
  return Object.values(raw.agents).map(mapAgentMetrics);
}

/** Fetches overall system health. Corresponds to `GET /health`.
 * NOTE: due to the route collision described on `ApiSimpleHealth`, this
 * endpoint returns a bare `{status, service, version}` object rather
 * than the richer per-component report `/health/pipeline` etc. return.
 * `message`/`lastCheckedAt` are populated as best as that shape allows. */
export async function getSystemHealth(
  signal?: AbortSignal
): Promise<ComponentHealth> {
  const raw = await request<ApiSimpleHealth>(HEALTH_ENDPOINT, { signal });
  return {
    status: raw.status === "healthy" ? "healthy" : "offline",
    message: `${raw.service} v${raw.version}`,
    lastCheckedAt: new Date().toISOString(),
  };
}

/** Fetches pipeline health. Corresponds to `GET /health/pipeline`. */
export async function getPipelineHealth(
  signal?: AbortSignal
): Promise<ComponentHealth> {
  const raw = await request<ApiComponentHealth>(
    `${HEALTH_ENDPOINT}/pipeline`,
    { signal }
  );
  return mapComponentHealth(raw);
}

/** Fetches storage health. Corresponds to `GET /health/storage`. */
export async function getStorageHealth(
  signal?: AbortSignal
): Promise<ComponentHealth> {
  const raw = await request<ApiComponentHealth>(`${HEALTH_ENDPOINT}/storage`, {
    signal,
  });
  return mapComponentHealth(raw);
}

/** Fetches model-serving health. Corresponds to `GET /health/models`. */
export async function getModelsHealth(
  signal?: AbortSignal
): Promise<ComponentHealth> {
  const raw = await request<ApiComponentHealth>(`${HEALTH_ENDPOINT}/models`, {
    signal,
  });
  return mapComponentHealth(raw);
}

/**
 * Fetches every metric and health check the Monitoring page needs in
 * parallel and assembles them into a single snapshot. Throws a single
 * `MonitoringServiceError` if any call fails, so the page can drive one
 * loading/error state instead of ten independent ones.
 */
export async function getMonitoringSnapshot(
  range: MonitoringTimeRange,
  signal?: AbortSignal
): Promise<MonitoringSnapshot> {
  try {
    const [
      overview,
      riskTrends,
      hallucinationTrends,
      validationTrends,
      requestVolume,
      agents,
      overall,
      pipeline,
      storage,
      models,
    ] = await Promise.all([
      getMetricsOverview(range, signal),
      getRiskTrends(range, signal),
      getHallucinationTrends(range, signal),
      getValidationTrends(range, signal),
      getPerformanceMetrics(range, signal),
      getAgentPerformance(signal),
      getSystemHealth(signal),
      getPipelineHealth(signal),
      getStorageHealth(signal),
      getModelsHealth(signal),
    ]);

    return {
      kpis: overview.kpis,
      riskTrends,
      hallucinationTrends,
      validationTrends,
      requestVolume,
      agents,
      health: { overall, pipeline, storage, models },
      fetchedAt: new Date().toISOString(),
    };
  } catch (error) {
    throw toServiceError(error);
  }
}
