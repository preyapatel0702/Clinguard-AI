import Badge from "../ui/badge/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../ui/table";
import { formatDateTime, severityToBadgeColor } from "../../utils/format";
import type { AuditHistoryEntry, AuditOutcome } from "../../types/audit";

interface AuditHistoryTableProps {
  entries: AuditHistoryEntry[];
  selectedSessionId?: string | null;
  onSelect: (entry: AuditHistoryEntry) => void;
}

function outcomeToBadgeColor(
  outcome: AuditOutcome
): "success" | "warning" | "error" | "light" {
  switch (outcome) {
    case "approved":
      return "success";
    case "flagged":
      return "warning";
    case "rejected":
      return "error";
    case "pending_review":
    default:
      return "light";
  }
}

function outcomeLabel(outcome: AuditOutcome): string {
  switch (outcome) {
    case "pending_review":
      return "pending review";
    default:
      return outcome;
  }
}

export default function AuditHistoryTable({
  entries,
  selectedSessionId,
  onSelect,
}: AuditHistoryTableProps) {
  return (
    <div className="max-w-full overflow-x-auto custom-scrollbar">
      <Table>
        <TableHeader className="border-b border-gray-100 dark:border-gray-800">
          <TableRow>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Session
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Model
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Risk
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Outcome
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Findings
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Created
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {entries.map((entry) => {
            const isSelected = entry.sessionId === selectedSessionId;
            return (
              <TableRow
                key={entry.sessionId}
                className={`cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-white/[0.03] ${
                  isSelected ? "bg-brand-50/60 dark:bg-brand-500/10" : ""
                }`}
              >
                <TableCell className="py-3">
                  <button
                    type="button"
                    onClick={() => onSelect(entry)}
                    className="block text-left text-theme-sm font-medium text-brand-500 hover:text-brand-600 hover:underline"
                  >
                    {entry.sessionId}
                  </button>
                  <span className="block max-w-xs truncate text-theme-xs text-gray-500 dark:text-gray-400">
                    {entry.summary}
                  </span>
                </TableCell>
                <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {entry.modelName}
                </TableCell>
                <TableCell className="py-3">
                  <Badge size="sm" color={severityToBadgeColor(entry.riskLevel)}>
                    {entry.riskLevel}
                  </Badge>
                </TableCell>
                <TableCell className="py-3">
                  <Badge size="sm" color={outcomeToBadgeColor(entry.outcome)}>
                    {outcomeLabel(entry.outcome)}
                  </Badge>
                </TableCell>
                <TableCell className="py-3 text-theme-xs text-gray-500 dark:text-gray-400">
                  {entry.hallucinationCount} hallucination
                  {entry.hallucinationCount === 1 ? "" : "s"} ·{" "}
                  {entry.validationFailureCount} validation failure
                  {entry.validationFailureCount === 1 ? "" : "s"}
                </TableCell>
                <TableCell className="py-3 text-theme-xs text-gray-500 dark:text-gray-400">
                  {formatDateTime(entry.createdAt)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
