"""
generator_agent.py
------------------
Phase 5 — Safe Response Generator Agent

Wraps SafeResponseGenerator and writes SafeResponseMetadata into the pipeline
context. Replaces the previous stub that simply returned the original response
for LOW/MODERATE risk cases.
"""

import time
import logging
from datetime import datetime, timezone


from backend.agents.base import BaseAgent
from backend.models.schemas import (
    PipelineContext,
    AgentTrace,
    AgentMessage,
    SafeResponse,
)
from backend.agents.generator_agent.response_generator import SafeResponseGenerator

logger = logging.getLogger("clinguard.observability")
DANGEROUS_PATTERNS = [
    "drink bleach",
    "consume bleach",
    "bleach mixed",
    "drink disinfectant",
    "kerosene",
    "gasoline",
    "turpentine",
    "stop insulin",
    "stop all medications",
    "skip chemotherapy",
    "avoid seeing a doctor",
    "don't see a doctor",
    "never see a doctor",
    "miracle cure",
    "guaranteed cure",
    "100% cure",
]


def contains_dangerous_advice(text: str) -> bool:
    text = text.lower()
    return any(pattern in text for pattern in DANGEROUS_PATTERNS)

class GeneratorAgent(BaseAgent):
    """
    Phase 5 — Intelligent Safe Response Generator Agent.

    Passes the raw AI response through SafeResponseGenerator which applies
    rule-based dangerous clause replacement, hallucination notices, risk-level
    preambles, and a mandatory disclaimer.
    """

    def __init__(self) -> None:
        self._generator = SafeResponseGenerator()

    @property
    def agent_name(self) -> str:
        return "GeneratorAgent"

    def process(self, context: PipelineContext) -> PipelineContext:
        start_time = time.perf_counter()
        logger.info("[GeneratorAgent] started")

        try:
            # ------------------------------------------------------------------
            # Generate safe response via SafeResponseGenerator
            # ------------------------------------------------------------------
            metadata = self._generator.generate(
                original=context.ai_response,
                hallucinations=context.hallucinations,
                risk_level=context.risk_level,
                validations=context.validations,
            )

            # ------------------------------------------------------------------
            # Write safe response back to context
            # ------------------------------------------------------------------
            context.safe_response = metadata.safe_response

            # ------------------------------------------------------------------
            # Final safety gate
            # Never allow dangerous advice to leave the pipeline.
            # ------------------------------------------------------------------

            if (
                context.risk_level in ("HIGH", "CRITICAL")
                or context.hallucinations
                or contains_dangerous_advice(context.safe_response)
            ):

                context.safe_response = (
                    "⚠️ MEDICAL EMERGENCY POSSIBLE\n\n"

                    "Potentially unsafe medical advice was detected and has been removed.\n\n"

                    "The original response was blocked because it contained information that "
                    "could be harmful if followed.\n\n"

                    "Please consult a licensed healthcare professional before making any "
                    "medical decisions.\n\n"

                    "If this situation involves chest pain, severe breathing difficulty, "
                    "loss of consciousness, stroke symptoms, severe bleeding, or another "
                    "medical emergency, seek immediate emergency medical care.\n\n"

                    "IMPORTANT: This information is AI-generated and is not a substitute for "
                    "professional medical advice, diagnosis, or treatment."
                )

            # Store rich metadata
            context.metadata["safe_response_metadata"] = metadata.model_dump()

            # Backward-compatible SafeResponse object
            safe_response_obj = SafeResponse(
                original_response=metadata.original_response,
                safe_response=context.safe_response,
                modified=len(metadata.modifications_made) > 0,
            )
            context.metadata["safe_response_details"] = safe_response_obj.model_dump()

            logger.info(
                f"[GeneratorAgent] generated safe response "
                f"modifications={len(metadata.modifications_made)} "
                f"confidence={metadata.confidence:.3f} "
                f"risk_level={context.risk_level}"
            )
            status = "SUCCESS"

        except Exception as exc:
            logger.error(f"[GeneratorAgent] error: {exc}", exc_info=True)
            context.safe_response = (
                "An error occurred while generating a safe response. "
                "Please consult a licensed healthcare professional directly."
            )
            context.metadata["generator_error"] = str(exc)
            status = "FAILED"

        # ------------------------------------------------------------------
        # A2A message to EvaluatorAgent
        # ------------------------------------------------------------------
        msg = AgentMessage(
            sender=self.agent_name,
            receiver="EvaluatorAgent",
            payload=(
                f"Safe response generated. "
                f"Modifications: {len(context.metadata.get('safe_response_metadata', {}).get('modifications_made', []))}. "
                f"Confidence: {context.metadata.get('safe_response_metadata', {}).get('confidence', 0):.3f}."
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        context.metadata.setdefault("message_history", []).append(msg.model_dump())

        # ------------------------------------------------------------------
        # Trace
        # ------------------------------------------------------------------
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"[GeneratorAgent] completed time={elapsed:.2f}ms status={status}")

        trace = AgentTrace(
            agent_name=self.agent_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=elapsed,
            status=status,
        )
        context.traces.append(trace)
        return context
