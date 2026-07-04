import type { FormEvent } from "react";
import type { AuditRiskLevel, AuditSearchFilters } from "../../types/audit";

interface AuditFiltersBarProps {
  filters: AuditSearchFilters;
  onChange: (filters: AuditSearchFilters) => void;
  onSubmit: (patientId: string) => void;
  isSearching?: boolean;
}

const RISK_OPTIONS: { value: AuditRiskLevel | "all"; label: string }[] = [
  { value: "all", label: "All risk levels" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
  { value: "info", label: "Info" },
];

export default function AuditFiltersBar({
  filters,
  onChange,
  onSubmit,
  isSearching = false,
}: AuditFiltersBarProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(filters.patientId.trim());
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end"
    >
      <div className="flex-1 min-w-[200px]">
        <label
          htmlFor="audit-patient-id"
          className="mb-1.5 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
        >
          Patient ID
        </label>
        <input
          id="audit-patient-id"
          type="text"
          value={filters.patientId}
          onChange={(event) =>
            onChange({ ...filters, patientId: event.target.value })
          }
          placeholder="e.g. PT-10245"
          className="h-10 w-full rounded-lg border border-gray-300 bg-transparent px-3 text-theme-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-gray-500"
        />
      </div>

      <div className="flex-1 min-w-[200px]">
        <label
          htmlFor="audit-session-query"
          className="mb-1.5 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
        >
          Session search
        </label>
        <input
          id="audit-session-query"
          type="text"
          value={filters.sessionQuery}
          onChange={(event) =>
            onChange({ ...filters, sessionQuery: event.target.value })
          }
          placeholder="Filter by session ID or summary"
          className="h-10 w-full rounded-lg border border-gray-300 bg-transparent px-3 text-theme-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-gray-500"
        />
      </div>

      <div className="min-w-[170px]">
        <label
          htmlFor="audit-risk-filter"
          className="mb-1.5 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
        >
          Risk level
        </label>
        <select
          id="audit-risk-filter"
          value={filters.riskLevel}
          onChange={(event) =>
            onChange({
              ...filters,
              riskLevel: event.target.value as AuditRiskLevel | "all",
            })
          }
          className="h-10 w-full rounded-lg border border-gray-300 bg-transparent px-3 text-theme-sm text-gray-800 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
        >
          {RISK_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        disabled={isSearching || filters.patientId.trim().length === 0}
        className="h-10 shrink-0 rounded-lg bg-brand-500 px-4 text-theme-sm font-medium text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSearching ? "Searching…" : "Search history"}
      </button>
    </form>
  );
}
