import type {
  AuditStatus,
  ModelStatus,
  PipelineRunStatus,
  PipelineStageStatus,
  Severity,
} from "../types";

/** Formats an ISO timestamp as e.g. "Jul 1, 2026, 3:45 PM". */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Formats an ISO timestamp as a coarse relative time, e.g. "5m ago". */
export function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffSec = Math.round(diffMs / 1000);

  if (diffSec < 60) return "just now";
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  return `${diffDay}d ago`;
}

export function formatPercent(value: number, fractionDigits = 1): string {
  return `${value.toFixed(fractionDigits)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat(undefined).format(value);
}

/** Formats a millisecond duration as e.g. "840ms" or "2.3s". */
export function formatDurationMs(durationMs: number): string {
  if (durationMs < 1000) return `${Math.round(durationMs)}ms`;
  return `${(durationMs / 1000).toFixed(1)}s`;
}

type BadgeColor =
  | "primary"
  | "success"
  | "error"
  | "warning"
  | "info"
  | "light"
  | "dark";

/** Maps a domain severity to the closest Badge color. */
export function severityToBadgeColor(severity: Severity): BadgeColor {
  switch (severity) {
    case "critical":
      return "error";
    case "high":
      return "warning";
    case "medium":
      return "info";
    case "low":
      return "success";
    case "info":
    default:
      return "light";
  }
}

export function auditStatusToBadgeColor(status: AuditStatus): BadgeColor {
  switch (status) {
    case "success":
      return "success";
    case "flagged":
      return "warning";
    case "failed":
      return "error";
    default:
      return "light";
  }
}

export function modelStatusToBadgeColor(status: ModelStatus): BadgeColor {
  switch (status) {
    case "healthy":
      return "success";
    case "degraded":
      return "warning";
    case "offline":
      return "error";
    default:
      return "light";
  }
}

export function pipelineRunStatusToBadgeColor(
  status: PipelineRunStatus
): BadgeColor {
  switch (status) {
    case "completed":
      return "success";
    case "running":
      return "info";
    case "queued":
      return "light";
    case "failed":
      return "error";
    default:
      return "light";
  }
}

export function pipelineStageStatusToBadgeColor(
  status: PipelineStageStatus
): BadgeColor {
  switch (status) {
    case "completed":
      return "success";
    case "running":
      return "info";
    case "pending":
      return "light";
    case "skipped":
      return "dark";
    case "failed":
      return "error";
    default:
      return "light";
  }
}
