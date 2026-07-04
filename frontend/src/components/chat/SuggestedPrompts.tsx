import { SUGGESTED_PROMPTS } from "../../services/chat";

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

export default function SuggestedPrompts({ onSelect }: SuggestedPromptsProps) {
  return (
    <div className="w-full max-w-xl text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-500 dark:bg-brand-500/15 dark:text-brand-400">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M12 3C7.02944 3 3 6.58172 3 11C3 13.0902 3.84547 14.9902 5.22834 16.4126C5.32926 16.5162 5.39292 16.6497 5.39292 16.7936V19.75C5.39292 20.1642 5.79381 20.4457 6.16995 20.2782L9.34047 18.858C9.53321 18.7716 9.75207 18.7568 9.9558 18.8032C10.6046 18.9509 11.2887 19 12 19C16.9706 19 21 15.4183 21 11C21 6.58172 16.9706 3 12 3Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h2 className="text-theme-xl font-semibold text-gray-800 dark:text-white/90">
        Ask the ClinGuard-AI assistant
      </h2>
      <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
        Get help interpreting audit events, model monitoring signals, and
        pipeline runs.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTED_PROMPTS.map((suggestion) => (
          <button
            key={suggestion.id}
            type="button"
            onClick={() => onSelect(suggestion.prompt)}
            className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-left text-theme-sm text-gray-700 shadow-theme-xs transition hover:border-brand-300 hover:bg-brand-25 dark:border-gray-800 dark:bg-white/[0.03] dark:text-gray-300 dark:hover:border-brand-800 dark:hover:bg-white/[0.06]"
          >
            {suggestion.label}
          </button>
        ))}
      </div>
    </div>
  );
}
