import EmptyState from "../common/EmptyState";

interface PipelineEmptyProps {
  title: string;
  description?: string;
}

export default function PipelineEmpty({
  title,
  description,
}: PipelineEmptyProps) {
  return (
    <EmptyState title={title} description={description} heightClass="h-64" />
  );
}
