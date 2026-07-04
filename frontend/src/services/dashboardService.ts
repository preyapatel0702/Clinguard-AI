// Dashboard data service for ClinGuard-AI.
//
// Composed from the real /metrics/* endpoints - there is no dedicated
// `/dashboard/summary` endpoint on the backend (this was checked against
// main.py, routers/, api/, and services/; no such route exists).
//
// Three widgets on the Dashboard page have no backing data source at all:
//   - recentAuditEntries: the backend only exposes per-session
//     (`GET /audit/{session_id}`) and per-patient (`GET /audit-history/{id}`)
//     lookups - there is no endpoint that lists recent sessions across all
//     patients, so this is always an empty array.
//   - activeAlerts: there is no alerts-list endpoint (alerts only appear
//     nested inside a single session's audit report).
//   - activePipelineRuns: the backend's "pipeline" is a per-request
//     execution (the 8-agent chain a single `/analyze` call runs through),
//     not a set of long-running/queued jobs - there is no endpoint that
//     lists in-flight pipeline runs.
// These are left as empty arrays (which the corresponding components
// already render as empty states) rather than inventing data for them.

import { ApiError, request } from "../api/client";
import type {
  ComplianceTrendPoint,
  DashboardSummary,
  KpiStat,
  SeverityBreakdownPoint,
} from "../types";

const METRICS_ENDPOINT = import.meta.env.VITE_METRICS_ENDPOINT ?? "/metrics";

interface ApiMetricsOverview {
  total_requests: number;
  average_latency_ms: number;
  average_risk_score: number;
  hallucination_rate: number;
  validation_success_rate: number;
  alerts_generated: number;
  high_risk_cases: number;
  average_pipeline_execution_time_ms: number;
}

interface ApiPeriodStats {
  count: number;
  avg_risk_score: number | null;
  high_risk_cases: number;
}

interface ApiRiskTrendsResponse {
  daily: Record<string, ApiPeriodStats>;
}

export class DashboardServiceError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "DashboardServiceError";
    this.status = status;
  }
}

function buildKpis(overview: ApiMetricsOverview): KpiStat[] {
  return [
    {
      id: "total-requests",
      label: "Total Requests",
      value: overview.total_requests.toLocaleString(),
    },
    {
      id: "average-risk-score",
      label: "Average Risk Score",
      value: overview.average_risk_score.toFixed(3),
    },
    {
      id: "hallucination-rate",
      label: "Hallucination Rate",
      value: `${(overview.hallucination_rate * 100).toFixed(1)}%`,
    },
    {
      id: "validation-success-rate",
      label: "Validation Success Rate",
      value: `${(overview.validation_success_rate * 100).toFixed(1)}%`,
    },
  ];
}

/** Derives an approximate "compliance" trend from real daily risk
 * statistics: complianceScore = (1 - avg_risk_score) * 100, since the
 * backend has no direct compliance-score concept - only risk scores
 * (0 = safest, 1 = highest risk). `incidents` uses the real
 * `high_risk_cases` count for that day. */
function buildComplianceTrend(
  riskTrends: ApiRiskTrendsResponse
): ComplianceTrendPoint[] {
  return Object.entries(riskTrends.daily)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([label, stats]) => ({
      label,
      complianceScore:
        stats.avg_risk_score != null
          ? Math.round((1 - stats.avg_risk_score) * 1000) / 10
          : 100,
      incidents: stats.high_risk_cases,
    }));
}

export async function getDashboardSummary(
  signal?: AbortSignal
): Promise<DashboardSummary> {
  try {
    const [overview, riskTrends] = await Promise.all([
      request<ApiMetricsOverview>(`${METRICS_ENDPOINT}/overview`, { signal }),
      request<ApiRiskTrendsResponse>(`${METRICS_ENDPOINT}/risk-trends`, {
        signal,
      }),
    ]);

    // No backend endpoint provides a severity-category breakdown
    // (critical/high/medium/low/info counts) anywhere - individual
    // hallucination findings have a confidence score but aggregate
    // stats are never bucketed by severity. Left empty rather than
    // invented; see module header note.
    const severityBreakdown: SeverityBreakdownPoint[] = [];

    return {
      kpis: buildKpis(overview),
      complianceTrend: buildComplianceTrend(riskTrends),
      severityBreakdown,
      recentAuditEntries: [],
      activeAlerts: [],
      activePipelineRuns: [],
    };
  } catch (error) {
    if (error instanceof ApiError) {
      throw new DashboardServiceError(
        error.status >= 500
          ? "The dashboard metrics service is temporarily unavailable. Please try again."
          : "The dashboard metrics service could not process that request.",
        error.status
      );
    }
    throw new DashboardServiceError(
      "Unable to reach the dashboard metrics service. Check your connection and try again."
    );
  }
}
