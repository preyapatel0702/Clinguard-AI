interface EmptyStateProps {
  title: string;
  description?: string;
  /** Tailwind height utility, e.g. "h-48" or "h-64". Defaults to "h-48". */
  heightClass?: string;
  icon?: React.ReactNode;
  className?: string;
}

/**
 * Generic empty-state placeholder used across Audit, Pipeline and Monitoring
 * views whenever a query returns no data. Kept intentionally minimal and
 * unopinionated about copy so each domain can supply its own title/description.
 */
export default function EmptyState({
  title,
  description,
  heightClass = "h-48",
  icon,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={`flex ${heightClass} flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed border-gray-200 px-6 text-center dark:border-gray-800 ${className}`}
    >
      {icon && (
        <span className="mb-1 text-gray-300 dark:text-gray-600" aria-hidden="true">
          {icon}
        </span>
      )}
      <p className="text-theme-sm font-medium text-gray-700 dark:text-gray-300">
        {title}
      </p>
      {description && (
        <p className="max-w-sm text-theme-xs text-gray-500 dark:text-gray-400">
          {description}
        </p>
      )}
    </div>
  );
}
