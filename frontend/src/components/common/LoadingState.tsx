interface LoadingStateProps {
  label?: string;
  /** Tailwind height utility, e.g. "h-48" or "h-64". Defaults to "h-48". */
  heightClass?: string;
  className?: string;
}

/**
 * Generic inline loading indicator used across Audit, Pipeline and Monitoring
 * views while a request is in flight.
 */
export default function LoadingState({
  label = "Loading…",
  heightClass = "h-48",
  className = "",
}: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex ${heightClass} flex-col items-center justify-center gap-3 text-theme-sm text-gray-500 dark:text-gray-400 ${className}`}
    >
      <span
        className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-brand-500 dark:border-gray-700 dark:border-t-brand-400"
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}
