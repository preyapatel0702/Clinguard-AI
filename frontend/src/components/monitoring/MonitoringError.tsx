import ErrorState from "../common/ErrorState";

interface MonitoringErrorProps {
  message: string;
  onRetry?: () => void;
}

export default function MonitoringError({
  message,
  onRetry,
}: MonitoringErrorProps) {
  return <ErrorState message={message} onRetry={onRetry} heightClass="h-64" />;
}
