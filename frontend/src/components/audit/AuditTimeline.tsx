import AuditEmptyState from "./AuditEmptyState";
import { formatDateTime } from "../../utils/format";
import type {
  AuditTimelineEvent,
  AuditTimelineEventType,
} from "../../types/audit";

interface AuditTimelineProps {
  events: AuditTimelineEvent[];
}

const TYPE_DOT_COLOR: Record<AuditTimelineEventType, string> = {
  input: "bg-blue-light-500",
  processing: "bg-gray-400",
  decision: "bg-brand-500",
  validation: "bg-warning-500",
  output: "bg-success-500",
  alert: "bg-error-500",
};

export default function AuditTimeline({ events }: AuditTimelineProps) {
  if (events.length === 0) {
    return (
      <AuditEmptyState
        title="No timeline events"
        description="This session did not record any timeline activity."
      />
    );
  }

  return (
    <ol className="relative ml-2 space-y-6 border-l border-gray-200 dark:border-gray-800">
      {events.map((event) => (
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
          {event.actor && (
            <p className="mt-0.5 text-theme-xs text-gray-400 dark:text-gray-500">
              Actor: {event.actor}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
