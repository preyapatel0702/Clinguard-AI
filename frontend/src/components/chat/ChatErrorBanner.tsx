interface ChatErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

export default function ChatErrorBanner({
  message,
  onDismiss,
}: ChatErrorBannerProps) {
  return (
    <div
      role="alert"
      className="mx-1 mb-2 flex items-center justify-between gap-3 rounded-lg border border-error-200 bg-error-50 px-3 py-2 text-theme-xs text-error-600 dark:border-error-500/30 dark:bg-error-500/10 dark:text-error-400"
    >
      <span>{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss error"
        className="shrink-0 rounded px-1.5 py-0.5 font-medium hover:bg-error-100 dark:hover:bg-error-500/20"
      >
        Dismiss
      </button>
    </div>
  );
}
