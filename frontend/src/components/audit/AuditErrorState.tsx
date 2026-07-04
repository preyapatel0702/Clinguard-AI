import ErrorState from "../common/ErrorState";

interface AuditErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function AuditErrorState({
  message,
  onRetry,
}: AuditErrorStateProps) {
  return <ErrorState message={message} onRetry={onRetry} heightClass="h-48" />;
}
