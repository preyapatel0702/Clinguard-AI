import logging
from typing import Any

from backend.models.schemas import (
    AgentTimelineEvent,
    DecisionTrace,
    DecisionTraceNode,
    PipelineContext,
)


logger = logging.getLogger("clinguard.observability")


AGENT_ORDER = [
    "InterceptorAgent",
    "DetectorAgent",
    "ValidatorAgent",
    "RiskAgent",
    "GeneratorAgent",
    "EvaluatorAgent",
    "MemoryAgent",
    "AlertAgent",
]


class TimelineEngine:
    def timeline(self, context: PipelineContext) -> list[AgentTimelineEvent]:
        logger.info("phase9.timeline_generation started trace_count=%s", len(context.traces))
        events = [
            AgentTimelineEvent(
                agent=trace.agent_name,
                timestamp=trace.timestamp,
                duration_ms=round(trace.execution_time_ms, 3),
                status=trace.status,
            )
            for trace in context.traces
        ]
        events.sort(key=lambda event: event.timestamp)
        logger.info("phase9.timeline_generation completed event_count=%s", len(events))
        return events

    def decision_trace(self, context: PipelineContext) -> DecisionTrace:
        trace_by_agent = {trace.agent_name: trace for trace in context.traces}
        nodes: list[DecisionTraceNode] = []

        for agent in AGENT_ORDER:
            trace = trace_by_agent.get(agent)
            if trace is None:
                continue

            nodes.append(
                DecisionTraceNode(
                    agent=agent,
                    status=trace.status,
                    execution_time_ms=round(trace.execution_time_ms, 3),
                    timestamp=trace.timestamp,
                    inputs=self._inputs_for(agent, context),
                    outputs=self._outputs_for(agent, context),
                )
            )

        return DecisionTrace(nodes=nodes)

    def _inputs_for(self, agent: str, context: PipelineContext) -> dict[str, Any]:
        common_request = {
            "patient_id": context.patient_id,
            "query": context.query,
            "ai_response": context.ai_response,
        }
        mapping: dict[str, dict[str, Any]] = {
            "InterceptorAgent": common_request,
            "DetectorAgent": {"ai_response": context.ai_response},
            "ValidatorAgent": {
                "claims": [claim.model_dump() for claim in context.claims],
                "medical_entities": context.medical_entities,
            },
            "RiskAgent": {
                "hallucinations": [h.model_dump() for h in context.hallucinations],
                "validations": [v.model_dump() for v in context.validations],
                "patient_age": context.patient_age,
                "comorbidities": context.comorbidities,
            },
            "GeneratorAgent": {
                "risk_level": context.risk_level,
                "hallucinations": [h.model_dump() for h in context.hallucinations],
                "validations": [v.model_dump() for v in context.validations],
            },
            "EvaluatorAgent": {
                "safe_response": context.safe_response,
                "risk_level": context.risk_level,
            },
            "MemoryAgent": {"patient_id": context.patient_id},
            "AlertAgent": {
                "risk_level": context.risk_level,
                "risk_score": context.risk_score,
            },
        }
        return mapping.get(agent, {})

    def _outputs_for(self, agent: str, context: PipelineContext) -> dict[str, Any]:
        mapping: dict[str, dict[str, Any]] = {
            "InterceptorAgent": {
                "message_history_count": len(context.metadata.get("message_history", [])),
            },
            "DetectorAgent": {
                "claims": [claim.model_dump() for claim in context.claims],
                "hallucinations": [h.model_dump() for h in context.hallucinations],
                "medical_entities": context.medical_entities,
            },
            "ValidatorAgent": {
                "validations": [validation.model_dump() for validation in context.validations],
            },
            "RiskAgent": {
                "risk_level": context.risk_level,
                "risk_score": context.risk_score,
                "risk_breakdown": (
                    context.risk_breakdown.model_dump()
                    if context.risk_breakdown else None
                ),
            },
            "GeneratorAgent": {
                "safe_response": context.safe_response,
                "safe_response_metadata": context.metadata.get("safe_response_metadata", {}),
            },
            "EvaluatorAgent": {
                "evaluation_report": (
                    context.evaluation_report.model_dump()
                    if context.evaluation_report else None
                ),
            },
            "MemoryAgent": {
                "session_id": context.metadata.get("session_id"),
                "memory_saved": context.metadata.get("memory_saved", False),
            },
            "AlertAgent": {
                "alerts": [alert.model_dump() for alert in context.alerts],
            },
        }
        return mapping.get(agent, {})
