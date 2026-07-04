import AuditEmptyState from "./AuditEmptyState";
import type { AuditDecisionStep } from "../../types/audit";

interface AuditDecisionTraceProps {
  steps: AuditDecisionStep[];
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "bg-success-500";
  if (confidence >= 0.5) return "bg-warning-500";
  return "bg-error-500";
}

export default function AuditDecisionTrace({ steps }: AuditDecisionTraceProps) {
  if (steps.length === 0) {
    return (
      <AuditEmptyState
        title="No decision trace"
        description="This session did not record a step-by-step decision trace."
      />
    );
  }

  const ordered = [...steps].sort((a, b) => a.order - b.order);

  return (
    <div className="space-y-4">
      {ordered.map((step) => (
        <div
          key={step.id}
          className="rounded-xl border border-gray-200 p-4 dark:border-gray-800"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
              <span className="mr-2 text-gray-400 dark:text-gray-500">
                Step {step.order}
              </span>
              {step.title}
            </p>
            {step.durationMs !== undefined && (
              <span className="text-theme-xs text-gray-400 dark:text-gray-500">
                {step.durationMs} ms
              </span>
            )}
          </div>

          <p className="mt-1.5 text-theme-sm text-gray-500 dark:text-gray-400">
            {step.description}
          </p>

          {step.confidence !== undefined && (
            <div className="mt-3 flex items-center gap-2">
              <div className="h-1.5 w-32 overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
                <div
                  className={`h-full rounded-full ${confidenceColor(step.confidence)}`}
                  style={{ width: `${Math.round(step.confidence * 100)}%` }}
                />
              </div>
              <span className="text-theme-xs text-gray-400 dark:text-gray-500">
                {Math.round(step.confidence * 100)}% confidence
              </span>
            </div>
          )}

          {(step.inputSummary || step.outputSummary) && (
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {step.inputSummary && (
                <div className="rounded-lg bg-gray-50 p-2.5 dark:bg-white/[0.03]">
                  <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                    Input
                  </p>
                  <p className="mt-0.5 text-theme-xs text-gray-600 dark:text-gray-300">
                    {step.inputSummary}
                  </p>
                </div>
              )}
              {step.outputSummary && (
                <div className="rounded-lg bg-gray-50 p-2.5 dark:bg-white/[0.03]">
                  <p className="text-theme-xs font-medium text-gray-500 dark:text-gray-400">
                    Output
                  </p>
                  <p className="mt-0.5 text-theme-xs text-gray-600 dark:text-gray-300">
                    {step.outputSummary}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
