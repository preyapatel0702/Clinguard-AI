import SystemHealthCards from "./SystemHealthCards";
import KpiGrid from "../dashboard/KpiGrid";
import type { KpiStat } from "../../types";
import type { SystemHealthSnapshot } from "../../types/monitoring";

interface MonitoringOverviewProps {
  kpis: KpiStat[];
  health: SystemHealthSnapshot;
}

export default function MonitoringOverview({
  kpis,
  health,
}: MonitoringOverviewProps) {
  return (
    <div className="space-y-4 md:space-y-6">
      <KpiGrid stats={kpis} />
      <SystemHealthCards health={health} />
    </div>
  );
}
