import { Link } from "react-router";
import ComponentCard from "../common/ComponentCard";
import Badge from "../ui/badge/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../ui/table";
import { auditStatusToBadgeColor, formatRelativeTime } from "../../utils/format";
import type { AuditLogEntry } from "../../types";

interface RecentAuditTableProps {
  entries: AuditLogEntry[];
}

export default function RecentAuditTable({ entries }: RecentAuditTableProps) {
  return (
    <ComponentCard
      title="Recent Audit Activity"
      desc="Latest logged actions across the platform"
      className="col-span-12"
    >
      <div className="max-w-full overflow-x-auto custom-scrollbar">
        <Table>
          <TableHeader className="border-b border-gray-100 dark:border-gray-800">
            <TableRow>
              <TableCell
                isHeader
                className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
              >
                Actor
              </TableCell>
              <TableCell
                isHeader
                className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
              >
                Action
              </TableCell>
              <TableCell
                isHeader
                className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
              >
                Resource
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
                When
              </TableCell>
            </TableRow>
          </TableHeader>

          <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
            {entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="py-3">
                  <div>
                    <span className="block text-theme-sm font-medium text-gray-800 dark:text-white/90">
                      {entry.actor}
                    </span>
                    <span className="block text-theme-xs text-gray-500 dark:text-gray-400">
                      {entry.actorRole}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {entry.action}
                </TableCell>
                <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                  {entry.resource}
                </TableCell>
                <TableCell className="py-3">
                  <Badge size="sm" color={auditStatusToBadgeColor(entry.status)}>
                    {entry.status}
                  </Badge>
                </TableCell>
                <TableCell className="py-3 text-theme-xs text-gray-500 dark:text-gray-400">
                  {formatRelativeTime(entry.timestamp)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="mt-4 text-right">
        <Link
          to="/audit"
          className="text-theme-sm font-medium text-brand-500 hover:text-brand-600"
        >
          View full audit log &rarr;
        </Link>
      </div>
    </ComponentCard>
  );
}
