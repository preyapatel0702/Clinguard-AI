import { Link } from "react-router";
import ComponentCard from "../common/ComponentCard";
import Badge from "../ui/badge/Badge";
import { formatRelativeTime, severityToBadgeColor } from "../../utils/format";
import type { MonitoringAlert } from "../../types";

interface ActiveAlertsListProps {
  alerts: MonitoringAlert[];
}

export default function ActiveAlertsList({ alerts }: ActiveAlertsListProps) {
  return (
    <ComponentCard title="Active Alerts" desc="Unacknowledged monitoring alerts">
      {alerts.length === 0 ? (
        <p className="text-theme-sm text-gray-500 dark:text-gray-400">
          No active alerts. Everything is quiet.
        </p>
      ) : (
        <ul className="flex flex-col gap-4">
          {alerts.map((alert) => (
            <li
              key={alert.id}
              className="flex items-start justify-between gap-3 border-b border-gray-100 pb-4 last:border-0 last:pb-0 dark:border-gray-800"
            >
              <div>
                <p className="text-theme-sm font-medium text-gray-800 dark:text-white/90">
                  {alert.title}
                </p>
                <p className="mt-0.5 text-theme-xs text-gray-500 dark:text-gray-400">
                  {alert.description}
                </p>
                <p className="mt-1 text-theme-xs text-gray-400 dark:text-gray-500">
                  {alert.source} &middot; {formatRelativeTime(alert.timestamp)}
                </p>
              </div>
              <Badge size="sm" color={severityToBadgeColor(alert.severity)}>
                {alert.severity}
              </Badge>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 text-right">
        <Link
          to="/monitoring"
          className="text-theme-sm font-medium text-brand-500 hover:text-brand-600"
        >
          View monitoring &rarr;
        </Link>
      </div>
    </ComponentCard>
  );
}
