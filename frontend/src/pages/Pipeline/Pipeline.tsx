import { type FormEvent, useEffect, useState } from "react";
import {
  ActiveSessionCard,
  AgentDetailsDrawer,
  PipelineEmpty,
  PipelineError,
  PipelineFlow,
  PipelineLoading,
  PipelineSummary,
  PipelineTimeline,
} from "../../components/pipeline";
import ComponentCard from "../../components/common/ComponentCard";
import PageMeta from "../../components/common/PageMeta";
import { getPipelineExecutionBySessionId } from "../../services/pipeline";
import type {
  PipelineAgentId,
  PipelineExecutionReport,
} from "../../types/pipeline";

type PageStatus = "idle" | "loading" | "loaded" | "error";

export default function Pipeline() {
  const [sessionIdInput, setSessionIdInput] = useState("");
  const [searchedSessionId, setSearchedSessionId] = useState<string | null>(
    null
  );
  const [report, setReport] = useState<PipelineExecutionReport | null>(null);
  const [status, setStatus] = useState<PageStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] =
    useState<PipelineAgentId | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!searchedSessionId) return;

    const controller = new AbortController();
    setStatus("loading");
    setError(null);
    setSelectedAgentId(null);

    getPipelineExecutionBySessionId(searchedSessionId, controller.signal)
      .then((data) => {
        setReport(data);
        setStatus("loaded");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load this pipeline execution."
        );
        setReport(null);
        setStatus("error");
      });

    return () => controller.abort();
  }, [searchedSessionId, reloadToken]);

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = sessionIdInput.trim();
    if (!trimmed) return;
    setSearchedSessionId(trimmed);
  };

  const selectedAgent =
    report && selectedAgentId
      ? report.agents.find((agent) => agent.id === selectedAgentId) ?? null
      : null;

  return (
    <>
      <PageMeta
        title="Pipeline | ClinGuard-AI"
        description="Live agent-by-agent execution graph for a clinical AI governance pipeline session: Interceptor, Detector, Validator, Risk, Generator, Evaluator, Memory, and Alert."
      />

      <ComponentCard
        title="Pipeline"
        desc="Look up a session to see how it moved through the Interceptor, Detector, Validator, Risk, Generator, Evaluator, Memory, and Alert agents."
      >
        <form
          onSubmit={handleSearch}
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <div className="flex-1 min-w-[200px]">
            <label
              htmlFor="pipeline-session-id"
              className="mb-1.5 block text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Session ID
            </label>
            <input
              id="pipeline-session-id"
              type="text"
              value={sessionIdInput}
              onChange={(event) => setSessionIdInput(event.target.value)}
              placeholder="e.g. sess-20260702-0143"
              className="h-10 w-full rounded-lg border border-gray-300 bg-transparent px-3 text-theme-sm text-gray-800 placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-gray-500"
            />
          </div>

          <button
            type="submit"
            disabled={status === "loading" || sessionIdInput.trim().length === 0}
            className="h-10 shrink-0 rounded-lg bg-brand-500 px-4 text-theme-sm font-medium text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === "loading" ? "Loading…" : "Load pipeline"}
          </button>
        </form>

        <div className="mt-6">
          {status === "idle" && (
            <PipelineEmpty
              title="Look up a session to get started"
              description="Enter a session ID above to load its pipeline execution."
            />
          )}

          {status === "loading" && (
            <PipelineLoading label="Loading pipeline execution…" />
          )}

          {status === "error" && error && (
            <PipelineError
              message={error}
              onRetry={() => setReloadToken((token) => token + 1)}
            />
          )}

          {status === "loaded" && report && (
            <div className="space-y-6">
              <ActiveSessionCard report={report} />

              <PipelineSummary report={report} />

              <div>
                <h4 className="mb-3 text-theme-sm font-medium text-gray-700 dark:text-gray-300">
                  Agent flow
                </h4>
                <div className="overflow-x-auto pb-2">
                  <PipelineFlow
                    agents={report.agents}
                    selectedAgentId={selectedAgentId}
                    onSelectAgent={setSelectedAgentId}
                  />
                </div>
                <p className="mt-2 text-theme-xs text-gray-400 dark:text-gray-500">
                  Click a stage to see its actions, evidence, decisions, and
                  execution details.
                </p>
              </div>

              <div>
                <h4 className="mb-3 text-theme-sm font-medium text-gray-700 dark:text-gray-300">
                  Execution timeline
                </h4>
                <PipelineTimeline events={report.timeline} />
              </div>
            </div>
          )}
        </div>
      </ComponentCard>

      <AgentDetailsDrawer
        agent={selectedAgent}
        onClose={() => setSelectedAgentId(null)}
      />
    </>
  );
}
