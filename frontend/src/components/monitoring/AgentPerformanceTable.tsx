import ComponentCard from "../common/ComponentCard";
import Badge from "../ui/badge/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../ui/table";
import {
  formatNumber,
  formatPercent,
  formatRelativeTime,
  modelStatusToBadgeColor,
} from "../../utils/format";
import type { AgentPerformanceEntry } from "../../types/monitoring";

interface AgentPerformanceTableProps {
  agents: AgentPerformanceEntry[];
}

export default function AgentPerformanceTable({
  agents,
}: AgentPerformanceTableProps) {
  return (
    <ComponentCard
      title="Agent Performance"
      desc="Throughput, latency, and quality by agent"
    >
      {agents.length === 0 ? (
        <p className="text-theme-sm text-gray-500 dark:text-gray-400">
          No agents match the current filter.
        </p>
      ) : (
        <div className="max-w-full overflow-x-auto custom-scrollbar">
          <Table>
            <TableHeader className="border-b border-gray-100 dark:border-gray-800">
              <TableRow>
                <TableCell
                  isHeader
                  className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Agent
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
                  Requests
                </TableCell>
                <TableCell
                  isHeader
                  className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Avg latency
                </TableCell>
                <TableCell
                  isHeader
                  className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Success rate
                </TableCell>
                <TableCell
                  isHeader
                  className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Hallucination rate
                </TableCell>
                <TableCell
                  isHeader
                  className="py-3 text-left text-theme-xs font-medium text-gray-500 dark:text-gray-400"
                >
                  Last active
                </TableCell>
              </TableRow>
            </TableHeader>

            <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
              {agents.map((agent) => (
                <TableRow key={agent.id}>
                  <TableCell className="py-3 text-theme-sm font-medium text-gray-800 dark:text-white/90">
                    {agent.agentName}
                  </TableCell>
                  <TableCell className="py-3">
                    <Badge size="sm" color={modelStatusToBadgeColor(agent.status)}>
                      {agent.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                    {formatNumber(agent.requestsHandled)}
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                    {agent.avgLatencyMs} ms
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                    {formatPercent(agent.successRatePct)}
                  </TableCell>
                  <TableCell className="py-3 text-theme-sm text-gray-600 dark:text-gray-300">
                    {agent.hallucinationRatePct != null
                      ? formatPercent(agent.hallucinationRatePct)
                      : "—"}
                  </TableCell>
                  <TableCell className="py-3 text-theme-xs text-gray-500 dark:text-gray-400">
                    {formatRelativeTime(agent.lastActiveAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </ComponentCard>
  );
}
