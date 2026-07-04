import PipelineEmpty from "./PipelineEmpty";
import { formatDateTime } from "../../utils/format";
import {
  PIPELINE_AGENT_LABELS,
  type PipelineTimelineEvent,
  type PipelineTimelineEventType,
} from "../../types/pipeline";

interface PipelineTimelineProps {
  events: PipelineTimelineEvent[];
}

const TYPE_DOT_COLOR: Record<PipelineTimelineEventType, string> = {
  started: "bg-blue-light-500",
  agent_started: "bg-brand-500",
  agent_completed: "bg-success-500",
  agent_failed: "bg-error-500",
  alert_raised: "bg-warning-500",
  completed: "bg-gray-400",
};

export default function PipelineTimeline({ events }: PipelineTimelineProps) {
  if (events.length === 0) {
    return (
      <PipelineEmpty
        title="No timeline events"
        description="This session did not record any execution timeline."
      />
    );
  }

  const ordered = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <ol className="relative ml-2 space-y-6 border-l border-gray-200 dark:border-gray-800">
      {ordered.map((event) => (
        <li key={event.id} className="ml-5">
          <span
            className={`absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full ring-4 ring-white dark:ring-gray-900 ${TYPE_DOT_COLOR[event.type]}`}
            aria-hidden="true"
          />
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
            <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
              {event.title}
            </p>
            <time className="text-theme-xs text-gray-400 dark:text-gray-500">
              {formatDateTime(event.timestamp)}
            </time>
          </div>
          {event.description && (
            <p className="mt-0.5 text-theme-sm text-gray-500 dark:text-gray-400">
              {event.description}
            </p>
          )}
          {event.agentId && (
            <p className="mt-0.5 text-theme-xs text-gray-400 dark:text-gray-500">
              Agent: {PIPELINE_AGENT_LABELS[event.agentId]}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
