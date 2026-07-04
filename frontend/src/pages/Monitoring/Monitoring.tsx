import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AgentPerformanceTable,
  HallucinationChart,
  MonitoringError,
  MonitoringFilters,
  MonitoringLoading,
  MonitoringOverview,
  RequestVolumeChart,
  RiskTrendChart,
  ValidationChart,
} from "../../components/monitoring";
import PageMeta from "../../components/common/PageMeta";
import { getMonitoringSnapshot } from "../../services/monitoring";
import { formatRelativeTime } from "../../utils/format";
import type {
  MonitoringFiltersState,
  MonitoringSnapshot,
} from "../../types/monitoring";

const AUTO_REFRESH_MS = 30_000;

const INITIAL_FILTERS: MonitoringFiltersState = {
  timeRange: "24h",
  agentQuery: "",
};

type PageStatus = "loading" | "loaded" | "error";

export default function Monitoring() {
  const [filters, setFilters] = useState<MonitoringFiltersState>(
    INITIAL_FILTERS
  );
  const [snapshot, setSnapshot] = useState<MonitoringSnapshot | null>(null);
  const [status, setStatus] = useState<PageStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Kept in a ref so the auto-refresh interval always reads the latest
  // time range without needing to be torn down and rebuilt on every
  // filter change.
  const timeRangeRef = useRef(filters.timeRange);
  timeRangeRef.current = filters.timeRange;

  const fetchSnapshot = useCallback(
    async (options: { silent: boolean }, signal?: AbortSignal) => {
      if (options.silent) {
        setIsRefreshing(true);
      } else {
        setStatus("loading");
        setError(null);
      }

      try {
        const data = await getMonitoringSnapshot(timeRangeRef.current, signal);
        if (signal?.aborted) return;
        setSnapshot(data);
        setStatus("loaded");
        setError(null);
      } catch (err) {
        if (signal?.aborted) return;
        const message =
          err instanceof Error
            ? err.message
            : "Unable to load monitoring data.";
        if (options.silent) {
          // Keep showing the last good snapshot during background
          // refreshes; surface the failure without blowing away the page.
          setError(message);
        } else {
          setStatus("error");
          setError(message);
        }
      } finally {
        if (!signal?.aborted) setIsRefreshing(false);
      }
    },
    []
  );

  // Initial load and reload whenever the time range filter changes.
  useEffect(() => {
    const controller = new AbortController();
    fetchSnapshot({ silent: false }, controller.signal);
    return () => controller.abort();
  }, [fetchSnapshot, filters.timeRange]);

  // Auto-refresh every 30s, independent of the time range effect above so
  // it doesn't reset on unrelated filter changes (e.g. agent search).
  useEffect(() => {
    const interval = window.setInterval(() => {
      const controller = new AbortController();
      fetchSnapshot({ silent: true }, controller.signal);
    }, AUTO_REFRESH_MS);

    return () => window.clearInterval(interval);
  }, [fetchSnapshot]);

  const filteredAgents = useMemo(() => {
    if (!snapshot) return [];
    const query = filters.agentQuery.trim().toLowerCase();
    if (query.length === 0) return snapshot.agents;

    return snapshot.agents.filter(
      (agent) =>
        agent.agentName.toLowerCase().includes(query) ||
        agent.status.toLowerCase().includes(query)
    );
  }, [snapshot, filters.agentQuery]);

  return (
    <>
      <PageMeta
        title="Model Monitoring | ClinGuard-AI"
        description="Live health, drift, and latency monitoring for deployed clinical AI models."
      />

      <div className="space-y-4 md:space-y-6">
        <MonitoringFilters
          filters={filters}
          onChange={setFilters}
          isRefreshing={isRefreshing}
          lastUpdatedLabel={
            snapshot ? formatRelativeTime(snapshot.fetchedAt) : undefined
          }
        />

        {status === "loading" && <MonitoringLoading />}

        {status === "error" && !snapshot && (
          <MonitoringError
            message={error ?? "Unable to load monitoring data."}
            onRetry={() => fetchSnapshot({ silent: false })}
          />
        )}

        {snapshot && status !== "loading" && (
          <>
            {error && (
              <div
                role="alert"
                className="rounded-lg border border-warning-200 bg-warning-50 px-3.5 py-2.5 text-theme-xs text-warning-700 dark:border-warning-500/30 dark:bg-warning-500/10 dark:text-orange-400"
              >
                Last auto-refresh failed: {error} Showing the most recently
                loaded data.
              </div>
            )}

            <MonitoringOverview kpis={snapshot.kpis} health={snapshot.health} />

            <div className="grid grid-cols-1 gap-4 md:gap-6 xl:grid-cols-2">
              <RiskTrendChart data={snapshot.riskTrends} />
              <HallucinationChart data={snapshot.hallucinationTrends} />
              <ValidationChart data={snapshot.validationTrends} />
              <RequestVolumeChart data={snapshot.requestVolume} />
            </div>

            <AgentPerformanceTable agents={filteredAgents} />
          </>
        )}
      </div>
    </>
  );
}
