import KpiCard from "./KpiCard";
import type { KpiStat } from "../../types";

interface KpiGridProps {
  stats: KpiStat[];
}

export default function KpiGrid({ stats }: KpiGridProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-6 xl:grid-cols-4">
      {stats.map((stat) => (
        <KpiCard key={stat.id} stat={stat} />
      ))}
    </div>
  );
}
