interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  /** Tailwind height utility, e.g. "h-48" or "h-64". Defaults to "h-48". */
  heightClass?: string;
  className?: string;
}

/**
 * Generic error-state placeholder used across Audit, Pipeline and Monitoring
 * views whenever a request fails. Kept intentionally minimal so each domain
 * can supply its own message copy and retry handler.
 */
export default function ErrorState({
  message,
  onRetry,
  heightClass = "h-48",
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`flex ${heightClass} flex-col items-center justify-center gap-3 rounded-xl border border-error-200 bg-error-50 px-6 text-center dark:border-error-500/30 dark:bg-error-500/10 ${className}`}
    >
      <p className="text-theme-sm font-medium text-error-600 dark:text-error-400">
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg border border-error-300 px-3 py-1.5 text-theme-xs font-medium text-error-600 transition-colors hover:bg-error-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-error-500/50 dark:border-error-500/40 dark:text-error-400 dark:hover:bg-error-500/20"
        >
          Try again
        </button>
      )}
    </div>
  );
}
