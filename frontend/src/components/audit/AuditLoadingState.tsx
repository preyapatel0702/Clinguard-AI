import LoadingState from "../common/LoadingState";

interface AuditLoadingStateProps {
  label?: string;
}

export default function AuditLoadingState({
  label = "Loading…",
}: AuditLoadingStateProps) {
  return <LoadingState label={label} heightClass="h-48" />;
}
