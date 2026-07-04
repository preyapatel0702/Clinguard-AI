import Badge from "../ui/badge/Badge";
import {
  formatDateTime,
  formatRelativeTime,
  pipelineRunStatusToBadgeColor,
} from "../../utils/format";
import type { PipelineExecutionReport } from "../../types/pipeline";

interface ActiveSessionCardProps {
  report: PipelineExecutionReport;
}

export default function ActiveSessionCard({ report }: ActiveSessionCardProps) {
  const isActive = report.status === "running" || report.status === "queued";

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-800 dark:bg-white/[0.03] sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-theme-sm font-semibold text-gray-800 dark:text-white/90">
            Session {report.sessionId}
          </p>
          <Badge size="sm" color={pipelineRunStatusToBadgeColor(report.status)}>
            {report.status}
          </Badge>
          {isActive && (
            <span className="flex h-2 w-2 items-center justify-center">
              <span className="absolute h-2 w-2 animate-ping rounded-full bg-brand-400 opacity-75" />
              <span className="h-2 w-2 rounded-full bg-brand-500" />
            </span>
          )}
        </div>
        <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">
          {report.patientName ?? report.patientId ?? "Unknown patient"}
          {report.modelName ? ` · ${report.modelName}` : ""}
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-theme-xs text-gray-500 dark:text-gray-400 sm:text-right">
        <dt className="sm:hidden">Started</dt>
        <dd>
          <span className="sm:hidden">Started </span>
          {formatDateTime(report.startedAt)} (
          {formatRelativeTime(report.startedAt)})
        </dd>
        {report.completedAt && (
          <>
            <dt className="sm:hidden">Completed</dt>
            <dd>
              <span className="sm:hidden">Completed </span>
              {formatDateTime(report.completedAt)}
            </dd>
          </>
        )}
      </dl>
    </div>
  );
}
