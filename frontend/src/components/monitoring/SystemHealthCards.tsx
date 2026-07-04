import Badge from "../ui/badge/Badge";
import { formatRelativeTime, modelStatusToBadgeColor } from "../../utils/format";
import type { ComponentHealth, SystemHealthSnapshot } from "../../types/monitoring";

interface SystemHealthCardsProps {
  health: SystemHealthSnapshot;
}

const CARDS: { key: keyof SystemHealthSnapshot; label: string }[] = [
  { key: "overall", label: "Overall system" },
  { key: "pipeline", label: "Pipeline" },
  { key: "storage", label: "Storage" },
  { key: "models", label: "Model serving" },
];

function HealthCard({
  label,
  health,
}: {
  label: string;
  health: ComponentHealth;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        <Badge size="sm" color={modelStatusToBadgeColor(health.status)}>
          {health.status}
        </Badge>
      </div>

      <div className="mt-3 space-y-1 text-theme-xs text-gray-500 dark:text-gray-400">
        {health.uptimePct !== undefined && (
          <p>Uptime: {health.uptimePct.toFixed(2)}%</p>
        )}
        {health.latencyMs !== undefined && (
          <p>Latency: {health.latencyMs} ms</p>
        )}
        <p>Checked {formatRelativeTime(health.lastCheckedAt)}</p>
        {health.message && (
          <p className="text-gray-400 dark:text-gray-500">{health.message}</p>
        )}
      </div>
    </div>
  );
}

export default function SystemHealthCards({ health }: SystemHealthCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-6 xl:grid-cols-4">
      {CARDS.map((card) => (
        <HealthCard key={card.key} label={card.label} health={health[card.key]} />
      ))}
    </div>
  );
}
