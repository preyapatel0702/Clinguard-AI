import { memo } from "react";
import Badge from "../ui/badge/Badge";
import {
  formatDurationMs,
  pipelineStageStatusToBadgeColor,
} from "../../utils/format";
import {
  PIPELINE_AGENT_LABELS,
  type PipelineAgentNode,
} from "../../types/pipeline";

interface AgentNodeProps {
  agent: PipelineAgentNode;
  isSelected: boolean;
  onSelect: (agentId: PipelineAgentNode["id"]) => void;
}

const STATUS_RING: Record<string, string> = {
  completed: "ring-success-500/40",
  running: "ring-brand-500/50",
  pending: "ring-gray-200 dark:ring-gray-700",
  failed: "ring-error-500/50",
  skipped: "ring-gray-200 dark:ring-gray-700",
};

const STATUS_PULSE: Record<string, string> = {
  running: "animate-pulse",
};

function AgentNode({
  agent,
  isSelected,
  onSelect,
}: AgentNodeProps) {
  const label = PIPELINE_AGENT_LABELS[agent.id];
  const ringClass = STATUS_RING[agent.status] ?? STATUS_RING.pending;
  const pulseClass = STATUS_PULSE[agent.status] ?? "";

  return (
    <button
      type="button"
      onClick={() => onSelect(agent.id)}
      aria-pressed={isSelected}
      aria-label={`${label} — ${agent.status}${
        agent.durationMs !== undefined
          ? `, ${formatDurationMs(agent.durationMs)}`
          : ""
      }`}
      className={`group flex w-full flex-col gap-2 rounded-xl border bg-white p-3.5 text-left ring-1 transition-all hover:-translate-y-0.5 hover:shadow-theme-md focus:outline-hidden focus:ring-3 focus:ring-brand-500/30 dark:bg-white/[0.03] sm:w-44 ${ringClass} ${pulseClass} ${
        isSelected
          ? "border-brand-400 shadow-theme-md dark:border-brand-500"
          : "border-gray-200 dark:border-gray-800"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-theme-sm font-semibold text-gray-800 dark:text-white/90">
          {label}
        </span>
        <Badge size="sm" color={pipelineStageStatusToBadgeColor(agent.status)}>
          {agent.status}
        </Badge>
      </div>

      <div className="flex items-center justify-between text-theme-xs text-gray-400 dark:text-gray-500">
        <span>
          {agent.durationMs !== undefined
            ? formatDurationMs(agent.durationMs)
            : "—"}
        </span>
        {agent.confidence !== undefined && (
          <span>{Math.round(agent.confidence * 100)}% conf.</span>
        )}
      </div>

      {agent.summary && (
        <p className="line-clamp-2 text-theme-xs text-gray-500 dark:text-gray-400">
          {agent.summary}
        </p>
      )}
    </button>
  );
}

export default memo(AgentNode);
