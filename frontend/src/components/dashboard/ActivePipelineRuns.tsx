import { Link } from "react-router";
import ComponentCard from "../common/ComponentCard";
import Badge from "../ui/badge/Badge";
import { pipelineRunStatusToBadgeColor } from "../../utils/format";
import type { PipelineRun } from "../../types";

interface ActivePipelineRunsProps {
  runs: PipelineRun[];
}

export default function ActivePipelineRuns({ runs }: ActivePipelineRunsProps) {
  return (
    <ComponentCard
      title="Active Pipeline Runs"
      desc="Retraining and validation jobs in progress"
    >
      {runs.length === 0 ? (
        <p className="text-theme-sm text-gray-500 dark:text-gray-400">
          No pipelines are currently running.
        </p>
      ) : (
        <ul className="flex flex-col gap-5">
          {runs.map((run) => (
            <li key={run.id}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
                  {run.pipelineName}
                </p>
                <Badge size="sm" color={pipelineRunStatusToBadgeColor(run.status)}>
                  {run.status}
                </Badge>
              </div>
              <div className="mt-2 h-2 w-full rounded-full bg-gray-100 dark:bg-white/[0.06]">
                <div
                  className="h-2 rounded-full bg-brand-500"
                  style={{ width: `${run.progressPct}%` }}
                />
              </div>
              <p className="mt-1 text-theme-xs text-gray-400 dark:text-gray-500">
                {run.progressPct}% &middot; triggered by {run.triggeredBy}
              </p>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 text-right">
        <Link
          to="/pipeline"
          className="text-theme-sm font-medium text-brand-500 hover:text-brand-600"
        >
          View pipelines &rarr;
        </Link>
      </div>
    </ComponentCard>
  );
}
