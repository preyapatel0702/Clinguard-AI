import { useEffect, useMemo, useState } from "react";
import {
  AuditDetailDrawer,
  AuditEmptyState,
  AuditErrorState,
  AuditFiltersBar,
  AuditHistoryTable,
  AuditLoadingState,
} from "../../components/audit";
import ComponentCard from "../../components/common/ComponentCard";
import PageMeta from "../../components/common/PageMeta";
import { getAuditHistoryByPatientId } from "../../services/audit";
import type { AuditHistoryEntry, AuditSearchFilters } from "../../types/audit";

const INITIAL_FILTERS: AuditSearchFilters = {
  patientId: "",
  sessionQuery: "",
  riskLevel: "all",
};

type ListStatus = "idle" | "loading" | "loaded" | "error";

export default function Audit() {
  const [filters, setFilters] = useState<AuditSearchFilters>(INITIAL_FILTERS);
  const [searchedPatientId, setSearchedPatientId] = useState<string | null>(
    null
  );
  const [entries, setEntries] = useState<AuditHistoryEntry[]>([]);
  const [status, setStatus] = useState<ListStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null
  );
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!searchedPatientId) return;

    const controller = new AbortController();
    setStatus("loading");
    setError(null);

    getAuditHistoryByPatientId(searchedPatientId, controller.signal)
      .then((response) => {
        setEntries(response.entries);
        setStatus("loaded");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load audit history for this patient."
        );
        setEntries([]);
        setStatus("error");
      });

    return () => controller.abort();
  }, [searchedPatientId, reloadToken]);

  const handleSearch = (patientId: string) => {
    if (!patientId) return;
    setSearchedPatientId(patientId);
  };

  const filteredEntries = useMemo(() => {
    const query = filters.sessionQuery.trim().toLowerCase();

    return entries.filter((entry) => {
      const matchesRisk =
        filters.riskLevel === "all" || entry.riskLevel === filters.riskLevel;

      const matchesQuery =
        query.length === 0 ||
        entry.sessionId.toLowerCase().includes(query) ||
        entry.summary.toLowerCase().includes(query);

      return matchesRisk && matchesQuery;
    });
  }, [entries, filters.riskLevel, filters.sessionQuery]);

  return (
    <>
      <PageMeta
        title="Audit Log | ClinGuard-AI"
        description="Searchable audit trail of clinical AI decision sessions, including decision traces, explanations, hallucination findings, and validation results."
      />

      <ComponentCard
        title="Audit Log"
        desc="Search a patient's audit history, then open a session for its full decision trace, explanation, and validation record."
      >
        <AuditFiltersBar
          filters={filters}
          onChange={setFilters}
          onSubmit={handleSearch}
          isSearching={status === "loading"}
        />

        <div className="mt-6">
          {status === "idle" && (
            <AuditEmptyState
              title="Search for a patient to get started"
              description="Enter a patient ID above to load their audit session history."
            />
          )}

          {status === "loading" && (
            <AuditLoadingState label="Loading audit history…" />
          )}

          {status === "error" && error && (
            <AuditErrorState
              message={error}
              onRetry={() => setReloadToken((token) => token + 1)}
            />
          )}

          {status === "loaded" && filteredEntries.length === 0 && (
            <AuditEmptyState
              title="No matching audit sessions"
              description="Try a different session search term or risk filter."
            />
          )}

          {status === "loaded" && filteredEntries.length > 0 && (
            <AuditHistoryTable
              entries={filteredEntries}
              selectedSessionId={selectedSessionId}
              onSelect={(entry) => setSelectedSessionId(entry.sessionId)}
            />
          )}
        </div>
      </ComponentCard>

      <AuditDetailDrawer
        sessionId={selectedSessionId}
        onClose={() => setSelectedSessionId(null)}
      />
    </>
  );
}
