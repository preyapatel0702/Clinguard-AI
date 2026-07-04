import AuditEmptyState from "./AuditEmptyState";
import Badge from "../ui/badge/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../ui/table";
import type { ValidationCheck, ValidationStatus } from "../../types/audit";

interface ValidationTableProps {
  checks: ValidationCheck[];
}

function statusToBadgeColor(
  status: ValidationStatus
): "success" | "warning" | "error" {
  switch (status) {
    case "passed":
      return "success";
    case "warning":
      return "warning";
    case "failed":
    default:
      return "error";
  }
}

export default function ValidationTable({ checks }: ValidationTableProps) {
  if (checks.length === 0) {
    return (
      <AuditEmptyState
        title="No validation checks"
        description="No validation rules were run for this session."
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
              Check
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Category
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Status
            </TableCell>
            <TableCell
              isHeader
              className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
            >
              Details
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
          {checks.map((check) => (
            <TableRow key={check.id}>
              <TableCell className="py-3">
                <span className="block text-theme-sm font-medium text-gray-800 dark:text-white/90">
                  {check.name}
                </span>
                {check.ruleRef && (
                  <span className="block text-theme-xs text-gray-400 dark:text-gray-500">
                    {check.ruleRef}
                  </span>
                )}
              </TableCell>
              <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                {check.category}
              </TableCell>
              <TableCell className="py-3">
                <Badge size="sm" color={statusToBadgeColor(check.status)}>
                  {check.status}
                </Badge>
              </TableCell>
              <TableCell className="py-3 text-theme-sm text-gray-500 dark:text-gray-400">
                {check.details ?? "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
