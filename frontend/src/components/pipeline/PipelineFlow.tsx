import AgentNode from "./AgentNode";
import {
  PIPELINE_AGENT_ORDER,
  type PipelineAgentId,
  type PipelineAgentNode,
} from "../../types/pipeline";

interface PipelineFlowProps {
  agents: PipelineAgentNode[];
  selectedAgentId: PipelineAgentId | null;
  onSelectAgent: (agentId: PipelineAgentId) => void;
}

/** Arrow connector between two stages. Rotates from a downward chevron
 * (stacked mobile layout) to a rightward chevron (row layout on larger
 * screens) via the `sm:rotate-[-90deg]` flip. */
function Connector() {
  return (
    <div
      className="flex shrink-0 items-center justify-center text-gray-300 dark:text-gray-700"
      aria-hidden="true"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        className="rotate-90 sm:rotate-0"
      >
        <path
          d="M9 6l6 6-6 6"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

export default function PipelineFlow({
  agents,
  selectedAgentId,
  onSelectAgent,
}: PipelineFlowProps) {
  const byId = new Map(agents.map((agent) => [agent.id, agent]));
  const ordered = PIPELINE_AGENT_ORDER.map((id) => byId.get(id)).filter(
    (agent): agent is PipelineAgentNode => agent !== undefined
  );

  return (
    <div
      role="list"
      aria-label="Pipeline agent execution flow"
      className="flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-2"
    >
      {ordered.map((agent, index) => (
        <div key={agent.id} className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
          <div role="listitem">
            <AgentNode
              agent={agent}
              isSelected={selectedAgentId === agent.id}
              onSelect={onSelectAgent}
            />
          </div>
          {index < ordered.length - 1 && <Connector />}
        </div>
      ))}
    </div>
  );
}
