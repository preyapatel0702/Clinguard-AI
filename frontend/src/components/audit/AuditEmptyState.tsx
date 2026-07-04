import EmptyState from "../common/EmptyState";

interface AuditEmptyStateProps {
  title: string;
  description?: string;
}

export default function AuditEmptyState({
  title,
  description,
}: AuditEmptyStateProps) {
  return (
    <EmptyState title={title} description={description} heightClass="h-48" />
  );
}
