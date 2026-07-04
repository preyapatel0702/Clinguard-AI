import AuditEmptyState from "./AuditEmptyState";
import Badge from "../ui/badge/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../ui/table";
import { severityToBadgeColor } from "../../utils/format";
import type { HallucinationFinding } from "../../types/audit";

interface HallucinationTableProps {
  findings: HallucinationFinding[];
}

export default function HallucinationTable({
  findings,
}: HallucinationTableProps) {
  if (findings.length === 0) {
    return (
      <AuditEmptyState
        title="No hallucinations detected"
        description="No unverified or fabricated claims were flagged for this session."
      />
    );
  }

  return (
    <div className="max-w-full overflow-x-auto custom-scrollbar">
      <Table>
        <TableHeader className="border-b border-gray-100 dark:border-gray-800">
          <TableRow>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Claim
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Severity
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Confidence
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Verified
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {findings.map((finding) => (
            <TableRow key={finding.id}>
              <TableCell className="py-3">
                <span className="block text-theme-sm text-gray-700 dark:text-gray-200">
                  {finding.claim}
                </span>
                {finding.explanation && (
                  <span className="mt-0.5 block text-theme-xs text-gray-500 dark:text-gray-400">
                    {finding.explanation}
                  </span>
                )}
                {finding.sourceSpan && (
                  <span className="mt-0.5 block text-theme-xs italic text-gray-400 dark:text-gray-500">
                    Source: {finding.sourceSpan}
                  </span>
                )}
              </TableCell>
              <TableCell className="py-3">
                <Badge size="sm" color={severityToBadgeColor(finding.severity)}>
                  {finding.severity}
                </Badge>
              </TableCell>
              <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                {Math.round(finding.confidence * 100)}%
              </TableCell>
              <TableCell className="py-3">
                <Badge
                  size="sm"
                  color={finding.verified ? "success" : "error"}
                >
                  {finding.verified ? "Verified" : "Unverified"}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
