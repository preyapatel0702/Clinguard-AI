import type { MonitoringFiltersState, MonitoringTimeRange } from "../../types/monitoring";

interface MonitoringFiltersProps {
  filters: MonitoringFiltersState;
  onChange: (filters: MonitoringFiltersState) => void;
  lastUpdatedLabel?: string;
  isRefreshing?: boolean;
}

const TIME_RANGE_OPTIONS: { value: MonitoringTimeRange; label: string }[] = [
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

export default function MonitoringFilters({
  filters,
  onChange,
  lastUpdatedLabel,
  isRefreshing = false,
}: MonitoringFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
        <div className="min-w-[170px]">
          <label
            htmlFor="monitoring-time-range"
            className="mb-1.5 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
          >
            Time range
          </label>
          <select
            id="monitoring-time-range"
            value={filters.timeRange}
            onChange={(event) =>
              onChange({
                ...filters,
                timeRange: event.target.value as MonitoringTimeRange,
              })
            }
            className="h-10 w-full rounded-lg border border-gray-300 bg-transparent px-3 text-theme-sm text-gray-800 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
          >
            {TIME_RANGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[220px]">
          <label
            htmlFor="monitoring-agent-query"
            className="mb-1.5 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
          >
            Filter agents
          </label>
          <input
            id="monitoring-agent-query"
            type="text"
            value={filters.agentQuery}
            onChange={(event) =>
              onChange({ ...filters, agentQuery: event.target.value })
            }
            placeholder="Search by agent name or status"
            className="h-10 w-full rounded-lg border border-gray-300 bg-transparent px-3 text-theme-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-gray-500"
          />
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-theme-xs text-gray-400 dark:text-gray-500">
        {isRefreshing && (
          <span
            className="h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-brand-500 dark:border-gray-700 dark:border-t-brand-400"
            aria-hidden="true"
          />
        )}
        <span>
          {isRefreshing
            ? "Refreshing…"
            : lastUpdatedLabel
              ? `Updated ${lastUpdatedLabel} · auto-refreshes every 30s`
              : "Auto-refreshes every 30s"}
        </span>
      </div>
    </div>
  );
}
