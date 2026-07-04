interface MonitoringChartEmptyStateProps {
  message: string;
}

/** Small inline empty state used inside chart cards when a metrics
 * endpoint returns no data points for the selected range. */
export default function MonitoringChartEmptyState({
  message,
}: MonitoringChartEmptyStateProps) {
  return (
    <div className="flex h-[300px] items-center justify-center text-theme-sm text-gray-400 dark:text-gray-500">
      {message}
    </div>
  );
}
