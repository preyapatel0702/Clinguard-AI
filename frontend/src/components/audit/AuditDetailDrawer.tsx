import { useEffect, useState } from "react";
import AuditDecisionTrace from "./AuditDecisionTrace";
import AuditErrorState from "./AuditErrorState";
import AuditExplanationView from "./AuditExplanationView";
import AuditExportActions from "./AuditExportActions";
import AuditLoadingState from "./AuditLoadingState";
import AuditTimeline from "./AuditTimeline";
import HallucinationTable from "./HallucinationTable";
import ValidationTable from "./ValidationTable";
import Badge from "../ui/badge/Badge";
import { getAuditBySessionId } from "../../services/audit";
import { formatDateTime, severityToBadgeColor } from "../../utils/format";
import type { AuditReport } from "../../types/audit";

interface AuditDetailDrawerProps {
  sessionId: string | null;
  onClose: () => void;
}

type DetailTab =
  | "timeline"
  | "decision"
  | "explanation"
  | "hallucinations"
  | "validations";

const TABS: { id: DetailTab; label: string }[] = [
  { id: "timeline", label: "Timeline" },
  { id: "decision", label: "Decision trace" },
  { id: "explanation", label: "Explanation" },
  { id: "hallucinations", label: "Hallucinations" },
  { id: "validations", label: "Validations" },
];

export default function AuditDetailDrawer({
  sessionId,
  onClose,
}: AuditDetailDrawerProps) {
  const [report, setReport] = useState<AuditReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>("timeline");
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!sessionId) {
      setReport(null);
      setError(null);
      return;
    }

    const controller = new AbortController();
    setIsLoading(true);
    setError(null);
    setActiveTab("timeline");

    getAuditBySessionId(sessionId, controller.signal)
      .then((data) => {
        setReport(data);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load this audit report."
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, [sessionId, reloadToken]);

  const isOpen = sessionId !== null;

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <>
      {isOpen && (
        <button
          type="button"
          aria-label="Close audit detail"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-gray-900/40"
        />
      )}

      <aside
        role="dialog"
        aria-modal={isOpen}
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-xl shrink-0 flex-col border-l border-gray-200 bg-white shadow-theme-lg transition-transform duration-200 dark:border-gray-800 dark:bg-gray-900 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!isOpen}
        aria-label="Audit report detail"
      >
        <div className="flex items-start justify-between gap-3 border-b border-gray-100 px-5 py-4 dark:border-gray-800">
          <div className="min-w-0">
            <p className="text-theme-xs font-medium text-gray-400 dark:text-gray-500">
              Session
            </p>
            <h3 className="truncate text-base font-semibold text-gray-800 dark:text-white/90">
              {sessionId ?? ""}
            </h3>
            {report && (
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <Badge size="sm" color={severityToBadgeColor(report.riskLevel)}>
                  {report.riskLevel} risk
                </Badge>
                <Badge size="sm" color="light">
                  {report.outcome.replace("_", " ")}
                </Badge>
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50 dark:text-gray-400 dark:hover:bg-white/10"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M18 6 6 18M6 6l12 12"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto custom-scrollbar px-5 py-4">
          {isLoading && <AuditLoadingState label="Loading audit report…" />}

          {!isLoading && error && (
            <AuditErrorState
              message={error}
              onRetry={() => setReloadToken((token) => token + 1)}
            />
          )}

          {!isLoading && !error && report && (
            <div className="space-y-5">
              <div className="rounded-xl bg-gray-50 p-3.5 text-theme-sm text-gray-600 dark:bg-white/[0.03] dark:text-gray-300">
                <p>{report.summary}</p>
                <dl className="mt-2.5 grid grid-cols-2 gap-y-1 text-theme-xs text-gray-500 dark:text-gray-400">
                  <dt>Patient</dt>
                  <dd className="text-right">
                    {report.patientName ?? report.patientId}
                  </dd>
                  <dt>Model</dt>
                  <dd className="text-right">
                    {report.modelName}
                    {report.modelVersion ? ` (${report.modelVersion})` : ""}
                  </dd>
                  <dt>Created</dt>
                  <dd className="text-right">
                    {formatDateTime(report.createdAt)}
                  </dd>
                  {report.completedAt && (
                    <>
                      <dt>Completed</dt>
                      <dd className="text-right">
                        {formatDateTime(report.completedAt)}
                      </dd>
                    </>
                  )}
                </dl>
              </div>

              <AuditExportActions sessionId={report.sessionId} />

              <div>
                <div
                  role="tablist"
                  aria-label="Audit detail sections"
                  className="flex flex-wrap gap-1 border-b border-gray-100 dark:border-gray-800"
                >
                  {TABS.map((tab) => (
                    <button
                      key={tab.id}
                      type="button"
                      role="tab"
                      aria-selected={activeTab === tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`rounded-t-lg px-3 py-2 text-theme-xs font-medium transition-colors ${
                        activeTab === tab.id
                          ? "border-b-2 border-brand-500 text-brand-500"
                          : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="pt-4">
                  {activeTab === "timeline" && (
                    <AuditTimeline events={report.timeline} />
                  )}
                  {activeTab === "decision" && (
                    <AuditDecisionTrace steps={report.decisionTrace} />
                  )}
                  {activeTab === "explanation" && (
                    <AuditExplanationView explanation={report.explanation} />
                  )}
                  {activeTab === "hallucinations" && (
                    <HallucinationTable findings={report.hallucinations} />
                  )}
                  {activeTab === "validations" && (
                    <ValidationTable checks={report.validations} />
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
