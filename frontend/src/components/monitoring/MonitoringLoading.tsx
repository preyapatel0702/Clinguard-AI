import LoadingState from "../common/LoadingState";

interface MonitoringLoadingProps {
  label?: string;
}

export default function MonitoringLoading({
  label = "Loading monitoring data…",
}: MonitoringLoadingProps) {
  return <LoadingState label={label} heightClass="h-64" />;
}
