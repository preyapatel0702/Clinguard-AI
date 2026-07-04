import { useEffect, useState } from "react";
import PipelineEmpty from "./PipelineEmpty";
import Badge from "../ui/badge/Badge";
import {
  formatDateTime,
  formatDurationMs,
  pipelineStageStatusToBadgeColor,
} from "../../utils/format";
import {
  PIPELINE_AGENT_DESCRIPTIONS,
  PIPELINE_AGENT_LABELS,
  type PipelineAgentNode,
} from "../../types/pipeline";

interface AgentDetailsDrawerProps {
  agent: PipelineAgentNode | null;
  onClose: () => void;
}

type DetailTab = "actions" | "evidence" | "decisions" | "execution";

const TABS: { id: DetailTab; label: string }[] = [
  { id: "actions", label: "Actions" },
  { id: "evidence", label: "Evidence" },
  { id: "decisions", label: "Decisions" },
  { id: "execution", label: "Execution" },
];

function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "bg-success-500";
  if (confidence >= 0.5) return "bg-warning-500";
  return "bg-error-500";
}

export default function AgentDetailsDrawer({
  agent,
  onClose,
}: AgentDetailsDrawerProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("actions");

  useEffect(() => {
    setActiveTab("actions");
  }, [agent?.id]);

  const isOpen = agent !== null;
  const label = agent ? PIPELINE_AGENT_LABELS[agent.id] : "";

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
          aria-label="Close agent detail"
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
        aria-label="Agent execution detail"
      >
        <div className="flex items-start justify-between gap-3 border-b border-gray-100 px-5 py-4 dark:border-gray-800">
          <div className="min-w-0">
            <p className="text-theme-xs font-medium text-gray-400 dark:text-gray-500">
              Agent
            </p>
            <h3 className="truncate text-base font-semibold text-gray-800 dark:text-white/90">
              {label}
            </h3>
            {agent && (
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <Badge
                  size="sm"
                  color={pipelineStageStatusToBadgeColor(agent.status)}
                >
                  {agent.status}
                </Badge>
                {agent.durationMs !== undefined && (
                  <Badge size="sm" color="light">
                    {formatDurationMs(agent.durationMs)}
                  </Badge>
                )}
                {agent.confidence !== undefined && (
                  <Badge size="sm" color="light">
                    {Math.round(agent.confidence * 100)}% confidence
                  </Badge>
                )}
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
          {agent && (
            <div className="space-y-5">
              <div className="rounded-xl bg-gray-50 p-3.5 text-theme-sm text-gray-600 dark:bg-white/[0.03] dark:text-gray-300">
                <p>{agent.summary ?? PIPELINE_AGENT_DESCRIPTIONS[agent.id]}</p>
              </div>

              <div>
                <div
                  role="tablist"
                  aria-label="Agent detail sections"
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
                  {activeTab === "actions" &&
                    (agent.actions.length === 0 ? (
                      <PipelineEmpty
                        title="No actions recorded"
                        description="This agent did not record any discrete actions."
                      />
                    ) : (
                      <ol className="relative ml-2 space-y-5 border-l border-gray-200 dark:border-gray-800">
                        {agent.actions.map((action) => (
                          <li key={action.id} className="ml-5">
                            <span
                              className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-brand-500 ring-4 ring-white dark:ring-gray-900"
                              aria-hidden="true"
                            />
                            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                              <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
                                {action.label}
                              </p>
                              <time className="text-theme-xs text-gray-400 dark:text-gray-500">
                                {formatDateTime(action.timestamp)}
                              </time>
                            </div>
                            {action.detail && (
                              <p className="mt-0.5 text-theme-sm text-gray-500 dark:text-gray-400">
                                {action.detail}
                              </p>
                            )}
                          </li>
                        ))}
                      </ol>
                    ))}

                  {activeTab === "evidence" &&
                    (agent.evidence.length === 0 ? (
                      <PipelineEmpty
                        title="No evidence recorded"
                        description="This agent did not surface any supporting evidence."
                      />
                    ) : (
                      <div className="space-y-3">
                        {agent.evidence.map((item) => (
                          <div
                            key={item.id}
                            className="rounded-xl border border-gray-200 p-3.5 dark:border-gray-800"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
                                {item.label}
                              </p>
                              {item.source && (
                                <span className="text-theme-xs text-gray-400 dark:text-gray-500">
                                  {item.source}
                                </span>
                              )}
                            </div>
                            <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
                              {item.value}
                            </p>
                          </div>
                        ))}
                      </div>
                    ))}

                  {activeTab === "decisions" &&
                    (agent.decisions.length === 0 ? (
                      <PipelineEmpty
                        title="No decisions recorded"
                        description="This agent did not record any explicit decisions."
                      />
                    ) : (
                      <div className="space-y-3">
                        {agent.decisions.map((decision) => (
                          <div
                            key={decision.id}
                            className="rounded-xl border border-gray-200 p-3.5 dark:border-gray-800"
                          >
                            <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
                              {decision.description}
                            </p>
                            {decision.rationale && (
                              <p className="mt-1 text-theme-sm text-gray-500 dark:text-gray-400">
                                {decision.rationale}
                              </p>
                            )}
                            {decision.confidence !== undefined && (
                              <div className="mt-3 flex items-center gap-2">
                                <div className="h-1.5 w-32 overflow-hidden rounded-full bg-gray-100 dark:bg-white/10">
                                  <div
                                    className={`h-full rounded-full ${confidenceColor(
                                      decision.confidence
                                    )}`}
                                    style={{
                                      width: `${Math.round(
                                        decision.confidence * 100
                                      )}%`,
                                    }}
                                  />
                                </div>
                                <span className="text-theme-xs text-gray-400 dark:text-gray-500">
                                  {Math.round(decision.confidence * 100)}%
                                  confidence
                                </span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ))}

                  {activeTab === "execution" && (
                    <dl className="grid grid-cols-2 gap-y-2.5 text-theme-sm">
                      <dt className="text-gray-500 dark:text-gray-400">
                        Status
                      </dt>
                      <dd className="text-right text-gray-800 dark:text-white/90">
                        {agent.status}
                      </dd>
                      <dt className="text-gray-500 dark:text-gray-400">
                        Started
                      </dt>
                      <dd className="text-right text-gray-800 dark:text-white/90">
                        {agent.startedAt ? formatDateTime(agent.startedAt) : "—"}
                      </dd>
                      <dt className="text-gray-500 dark:text-gray-400">
                        Completed
                      </dt>
                      <dd className="text-right text-gray-800 dark:text-white/90">
                        {agent.completedAt
                          ? formatDateTime(agent.completedAt)
                          : "—"}
                      </dd>
                      <dt className="text-gray-500 dark:text-gray-400">
                        Duration
                      </dt>
                      <dd className="text-right text-gray-800 dark:text-white/90">
                        {agent.durationMs !== undefined
                          ? formatDurationMs(agent.durationMs)
                          : "—"}
                      </dd>
                      <dt className="text-gray-500 dark:text-gray-400">
                        Confidence
                      </dt>
                      <dd className="text-right text-gray-800 dark:text-white/90">
                        {agent.confidence !== undefined
                          ? `${Math.round(agent.confidence * 100)}%`
                          : "—"}
                      </dd>
                    </dl>
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
