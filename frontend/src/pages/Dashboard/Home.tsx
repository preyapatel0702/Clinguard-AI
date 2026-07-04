import { useEffect, useState } from "react";
import PageMeta from "../../components/common/PageMeta";
import KpiGrid from "../../components/dashboard/KpiGrid";
import ComplianceTrendChart from "../../components/dashboard/ComplianceTrendChart";
import SeverityBreakdownChart from "../../components/dashboard/SeverityBreakdownChart";
import RecentAuditTable from "../../components/dashboard/RecentAuditTable";
import ActiveAlertsList from "../../components/dashboard/ActiveAlertsList";
import ActivePipelineRuns from "../../components/dashboard/ActivePipelineRuns";
import {
  DashboardServiceError,
  getDashboardSummary,
} from "../../services/dashboardService";
import type { DashboardSummary } from "../../types";

type Status = "loading" | "loaded" | "error";

export default function Home() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    setError(null);

    getDashboardSummary(controller.signal)
      .then((data) => {
        setSummary(data);
        setStatus("loaded");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(
          err instanceof DashboardServiceError
            ? err.message
            : "Unable to load the dashboard."
        );
        setStatus("error");
      });

    return () => controller.abort();
  }, [reloadToken]);

  return (
    <>
      <PageMeta
        title="Dashboard | ClinGuard-AI"
        description="Clinical AI governance overview: compliance posture, active alerts, audit activity, and pipeline health."
      />

      {status === "loading" && (
        <div className="flex h-64 items-center justify-center text-theme-sm text-gray-500 dark:text-gray-400">
          Loading dashboard…
        </div>
      )}

      {status === "error" && (
        <div className="flex h-64 flex-col items-center justify-center gap-3 text-theme-sm text-gray-500 dark:text-gray-400">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => setReloadToken((token) => token + 1)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-theme-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
          >
            Retry
          </button>
        </div>
      )}

      {status === "loaded" && summary && (
        <div className="grid grid-cols-12 gap-4 md:gap-6">
          <div className="col-span-12">
            <KpiGrid stats={summary.kpis} />
          </div>

          <div className="col-span-12 xl:col-span-7">
            <ComplianceTrendChart data={summary.complianceTrend} />
          </div>

          <div className="col-span-12 xl:col-span-5">
            <SeverityBreakdownChart data={summary.severityBreakdown} />
          </div>

          <div className="col-span-12 xl:col-span-6">
            <ActiveAlertsList alerts={summary.activeAlerts} />
          </div>

          <div className="col-span-12 xl:col-span-6">
            <ActivePipelineRuns runs={summary.activePipelineRuns} />
          </div>

          <div className="col-span-12">
            <RecentAuditTable entries={summary.recentAuditEntries} />
          </div>
        </div>
      )}
    </>
  );
}
