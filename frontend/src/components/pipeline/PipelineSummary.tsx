import { formatDurationMs } from "../../utils/format";
import Badge from "../ui/badge/Badge";
import {
  pipelineRunStatusToBadgeColor,
  pipelineStageStatusToBadgeColor,
} from "../../utils/format";
import type {
  PipelineAgentNode,
  PipelineAgentStatus,
  PipelineExecutionReport,
} from "../../types/pipeline";

interface PipelineSummaryProps {
  report: PipelineExecutionReport;
}

function countByStatus(
  agents: PipelineAgentNode[]
): Record<PipelineAgentStatus, number> {
  const counts: Record<PipelineAgentStatus, number> = {
    completed: 0,
    running: 0,
    pending: 0,
    failed: 0,
    skipped: 0,
  };
  for (const agent of agents) {
    counts[agent.status] += 1;
  }
  return counts;
}

export default function PipelineSummary({ report }: PipelineSummaryProps) {
  const counts = countByStatus(report.agents);
  const totalLatency =
    report.totalLatencyMs ??
    report.agents.reduce((sum, agent) => sum + (agent.durationMs ?? 0), 0);

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div className="rounded-xl border border-gray-200 p-3.5 dark:border-gray-800">
        <p className="text-theme-xs text-gray-400 dark:text-gray-500">
          Pipeline status
        </p>
        <div className="mt-1.5">
          <Badge size="sm" color={pipelineRunStatusToBadgeColor(report.status)}>
            {report.status}
          </Badge>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 p-3.5 dark:border-gray-800">
        <p className="text-theme-xs text-gray-400 dark:text-gray-500">
          Total latency
        </p>
        <p className="mt-1.5 text-theme-sm font-semibold text-gray-800 dark:text-white/90">
          {formatDurationMs(totalLatency)}
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 p-3.5 dark:border-gray-800">
        <p className="text-theme-xs text-gray-400 dark:text-gray-500">
          Stages completed
        </p>
        <p className="mt-1.5 text-theme-sm font-semibold text-gray-800 dark:text-white/90">
          {counts.completed} / {report.agents.length}
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 p-3.5 dark:border-gray-800">
        <p className="text-theme-xs text-gray-400 dark:text-gray-500">
          Failures
        </p>
        <p
          className={`mt-1.5 text-theme-sm font-semibold ${
            counts.failed > 0
              ? "text-error-600 dark:text-error-400"
              : "text-gray-800 dark:text-white/90"
          }`}
        >
          {counts.failed}
        </p>
      </div>

      {(counts.running > 0 || counts.skipped > 0) && (
        <div className="col-span-2 flex flex-wrap items-center gap-1.5 sm:col-span-4">
          {counts.running > 0 && (
            <Badge size="sm" color={pipelineStageStatusToBadgeColor("running")}>
              {counts.running} running
            </Badge>
          )}
          {counts.skipped > 0 && (
            <Badge size="sm" color={pipelineStageStatusToBadgeColor("skipped")}>
              {counts.skipped} skipped
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
