import ErrorState from "../common/ErrorState";

interface PipelineErrorProps {
  message: string;
  onRetry?: () => void;
}

export default function PipelineError({
  message,
  onRetry,
}: PipelineErrorProps) {
  return <ErrorState message={message} onRetry={onRetry} heightClass="h-64" />;
}
