import time
from datetime import datetime,UTC
from typing import Any, Dict
from backend.agents.base import BaseAgent
from backend.models.schemas import PipelineContext, AgentTrace, AgentMessage

class InterceptorAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "InterceptorAgent"

    def process(self, context: PipelineContext) -> PipelineContext:
        start_time = time.perf_counter()
        
        # Initialize metadata and message history
        if not context.metadata:
            context.metadata = {}
        if "message_history" not in context.metadata:
            context.metadata["message_history"] = []

        status = "SUCCESS"
        # Validate request fields
        if not context.patient_id or not context.query or not context.ai_response:
            status = "FAILED"
            context.metadata["error"] = "Validation failed: patient_id, query, and ai_response are required."

        # Simulate A2A message to DetectorAgent
        msg = AgentMessage(
            sender=self.agent_name,
            receiver="DetectorAgent",
            payload="Request received and validated successfully. Forwarding context for hallucination detection.",
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z")
        )
        # Store message history as list of dicts to remain JSON serializable
        context.metadata["message_history"].append(msg.model_dump())

        end_time = time.perf_counter()
        execution_time_ms = (end_time - start_time) * 1000

        # Create first trace
        trace = AgentTrace(
            agent_name=self.agent_name,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            execution_time_ms=execution_time_ms,
            status=status
        )
        context.traces.append(trace)

        return context
