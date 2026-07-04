import type { AuditExplanation } from "../../types/audit";

interface AuditExplanationViewProps {
  explanation: AuditExplanation;
}

export default function AuditExplanationView({
  explanation,
}: AuditExplanationViewProps) {
  return (
    <div className="space-y-5">
      <div>
        <h4 className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
          Summary
        </h4>
        <p className="mt-1 text-theme-sm text-gray-600 dark:text-gray-300">
          {explanation.summary}
        </p>
      </div>

      {explanation.reasoning.length > 0 && (
        <div>
          <h4 className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
            Reasoning
          </h4>
          <ul className="mt-1.5 list-disc space-y-1 pl-5 text-theme-sm text-gray-600 dark:text-gray-300">
            {explanation.reasoning.map((point, index) => (
              <li key={index}>{point}</li>
            ))}
          </ul>
        </div>
      )}

      {explanation.factors.length > 0 && (
        <div>
          <h4 className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
            Contributing factors
          </h4>
          <div className="mt-2 space-y-2.5">
            {explanation.factors.map((factor) => (
              <div key={factor.name}>
                <div className="flex items-center justify-between text-theme-xs text-gray-500 dark:text-gray-400">
                  <span>{factor.name}</span>
                  <span>{Math.round(factor.weight * 100)}%</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${Math.round(factor.weight * 100)}%` }}
                  />
                </div>
                {factor.description && (
                  <p className="mt-1 text-theme-xs text-gray-500 dark:text-gray-400">
                    {factor.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {explanation.citations && explanation.citations.length > 0 && (
        <div>
          <h4 className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
            Citations
          </h4>
          <ul className="mt-1.5 list-disc space-y-1 pl-5 text-theme-xs text-gray-500 dark:text-gray-400">
            {explanation.citations.map((citation, index) => (
              <li key={index}>{citation}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
