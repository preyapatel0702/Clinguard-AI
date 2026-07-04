import { useState } from "react";
import { exportAudit, saveExportToDisk } from "../../services/audit";
import type { AuditExportFormat } from "../../types/audit";

interface AuditExportActionsProps {
  sessionId: string;
}

export default function AuditExportActions({
  sessionId,
}: AuditExportActionsProps) {
  const [pending, setPending] = useState<AuditExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async (format: AuditExportFormat) => {
    setPending(format);
    setError(null);
    try {
      const result = await exportAudit(sessionId, format);
      saveExportToDisk(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Unable to export the audit report as ${format.toUpperCase()}.`
      );
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => handleExport("json")}
          disabled={pending !== null}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-theme-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
        >
          {pending === "json" ? "Exporting JSON…" : "Export JSON"}
        </button>
        <button
          type="button"
          onClick={() => handleExport("pdf")}
          disabled={pending !== null}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-theme-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-white/5"
        >
          {pending === "pdf" ? "Exporting PDF…" : "Export PDF"}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-theme-xs text-error-600 dark:text-error-400">
          {error}
        </p>
      )}
    </div>
  );
}
