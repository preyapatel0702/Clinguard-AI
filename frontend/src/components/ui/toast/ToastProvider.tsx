import { useCallback, useMemo, useRef, useState } from "react";
import { ToastContext, type ToastOptions, type ToastVariant } from "./ToastContext";

interface ToastRecord extends Required<Omit<ToastOptions, "description">> {
  id: number;
  description?: string;
}

const VARIANT_STYLES: Record<
  ToastVariant,
  { border: string; icon: string; iconGlyph: string }
> = {
  success: {
    border: "border-l-4 border-success-500",
    icon: "bg-success-50 text-success-600 dark:bg-success-500/15 dark:text-success-500",
    iconGlyph: "✓",
  },
  error: {
    border: "border-l-4 border-error-500",
    icon: "bg-error-50 text-error-600 dark:bg-error-500/15 dark:text-error-500",
    iconGlyph: "!",
  },
  warning: {
    border: "border-l-4 border-warning-500",
    icon: "bg-warning-50 text-warning-600 dark:bg-warning-500/15 dark:text-orange-400",
    iconGlyph: "!",
  },
  info: {
    border: "border-l-4 border-blue-light-500",
    icon: "bg-blue-light-50 text-blue-light-500 dark:bg-blue-light-500/15 dark:text-blue-light-500",
    iconGlyph: "i",
  },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const nextId = useRef(0);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    ({ title, description, variant = "info", duration = 5000 }: ToastOptions) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, title, description, variant, duration }]);
      if (duration > 0) {
        window.setTimeout(() => dismissToast(id), duration);
      }
    },
    [dismissToast]
  );

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 top-4 z-99999 flex flex-col items-end gap-2 px-4 sm:top-6 sm:right-6 sm:left-auto"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((toast) => {
          const styles = VARIANT_STYLES[toast.variant];
          return (
            <div
              key={toast.id}
              role="status"
              className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl bg-white p-4 shadow-theme-lg animate-toast-in dark:bg-gray-dark ${styles.border}`}
            >
              <span
                aria-hidden="true"
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${styles.icon}`}
              >
                {styles.iconGlyph}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
                  {toast.title}
                </p>
                {toast.description && (
                  <p className="mt-0.5 text-theme-xs text-gray-500 dark:text-gray-400">
                    {toast.description}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                aria-label="Dismiss notification"
                className="shrink-0 rounded-md p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 dark:hover:bg-white/5 dark:hover:text-gray-300"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M6.22 6.22a.75.75 0 011.06 0L12 10.94l4.72-4.72a.75.75 0 111.06 1.06L13.06 12l4.72 4.72a.75.75 0 11-1.06 1.06L12 13.06l-4.72 4.72a.75.75 0 01-1.06-1.06L10.94 12 6.22 7.28a.75.75 0 010-1.06z"
                    fill="currentColor"
                  />
                </svg>
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
