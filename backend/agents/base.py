from abc import ABC, abstractmethod
from backend.models.schemas import PipelineContext

class BaseAgent(ABC):
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """
        Name of the agent.
        """
        pass

    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Accepts PipelineContext, processes it, and returns the updated PipelineContext.
        """
        pass
