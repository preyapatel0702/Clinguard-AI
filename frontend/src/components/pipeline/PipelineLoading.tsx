import LoadingState from "../common/LoadingState";

interface PipelineLoadingProps {
  label?: string;
}

export default function PipelineLoading({
  label = "Loading pipeline execution…",
}: PipelineLoadingProps) {
  return <LoadingState label={label} heightClass="h-64" />;
}
