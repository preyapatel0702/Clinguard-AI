"""
timeline_engine.py
------------------
Phase 9 — Chronological Execution Timeline

Converts ``AgentTrace`` records from PipelineContext into rich
``TimelineEvent`` objects that include start/end times, execution
duration, status, and a description of actions each agent performed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from backend.models.audit import TimelineEvent
from backend.models.schemas import PipelineContext

logger = logging.getLogger("clinguard.phase9.timeline")

# Canonical agent order used to infer actions when traces don't include
# explicit action metadata.
_AGENT_ORDER: List[str] = [
    "InterceptorAgent",
    "DetectorAgent",
    "ValidatorAgent",
    "RiskAgent",
    "GeneratorAgent",
    "EvaluatorAgent",
    "MemoryAgent",
    "AlertAgent",
]


class TimelineEngineV2:
    """Build a chronological timeline of agent executions."""

    def generate(self, context: PipelineContext) -> List[TimelineEvent]:
        """Return an ordered list of ``TimelineEvent`` objects."""
        logger.info(
            "timeline_engine.generate started trace_count=%d",
            len(context.traces),
        )
        events: List[TimelineEvent] = []

        for trace in context.traces:
            # Parse the recorded timestamp as the *end* time (agents log
            # their trace at the end of execution).
            end_dt = self._parse_iso(trace.timestamp)
            start_dt = end_dt - timedelta(milliseconds=trace.execution_time_ms)

            actions = self._infer_actions(trace.agent_name, context)

            events.append(
                TimelineEvent(
                    agent_name=trace.agent_name,
                    start_time=start_dt.isoformat(),
                    end_time=end_dt.isoformat(),
                    execution_time_ms=round(trace.execution_time_ms, 3),
                    status=trace.status,
                    actions_performed=actions,
                )
            )

        # Sort chronologically by start_time
        events.sort(key=lambda e: e.start_time)
        logger.info(
            "timeline_engine.generate completed event_count=%d",
            len(events),
        )
        return events

    # ------------------------------------------------------------------
    # Action inference
    # ------------------------------------------------------------------

    def _infer_actions(
        self, agent_name: str, context: PipelineContext
    ) -> List[str]:
        """Derive human-readable actions from pipeline state for *agent_name*."""
        dispatch: Dict[str, Any] = {
            "InterceptorAgent": self._interceptor_actions,
            "DetectorAgent": self._detector_actions,
            "ValidatorAgent": self._validator_actions,
            "RiskAgent": self._risk_actions,
            "GeneratorAgent": self._generator_actions,
            "EvaluatorAgent": self._evaluator_actions,
            "MemoryAgent": self._memory_actions,
            "AlertAgent": self._alert_actions,
        }
        handler = dispatch.get(agent_name)
        if handler is None:
            return [f"Executed {agent_name}"]
        return handler(context)

    @staticmethod
    def _interceptor_actions(ctx: PipelineContext) -> List[str]:
        return ["Validated request fields", "Initialised pipeline context"]

    @staticmethod
    def _detector_actions(ctx: PipelineContext) -> List[str]:
        actions: List[str] = ["Extracted medical entities"]
        entity_counts = {
            cat: len(ctx.medical_entities.get(cat, []))
            for cat in ("drugs", "diseases", "symptoms")
        }
        actions.append(
            f"Found {entity_counts['drugs']} drug(s), "
            f"{entity_counts['diseases']} disease(s), "
            f"{entity_counts['symptoms']} symptom(s)"
        )
        active = [h for h in ctx.hallucinations if h.is_hallucination]
        if active:
            actions.append(f"Detected {len(active)} hallucination(s)")
        else:
            actions.append("No hallucinations detected")
        return actions

    @staticmethod
    def _validator_actions(ctx: PipelineContext) -> List[str]:
        actions: List[str] = []
        supported = sum(1 for v in ctx.validations if v.is_valid)
        rejected = sum(1 for v in ctx.validations if not v.is_valid)
        actions.append(f"Validated {len(ctx.validations)} claim(s)")
        if supported:
            actions.append(f"{supported} claim(s) supported")
        if rejected:
            actions.append(f"{rejected} claim(s) rejected")
        return actions or ["No claims to validate"]

    @staticmethod
    def _risk_actions(ctx: PipelineContext) -> List[str]:
        actions = [
            f"Calculated risk score: {ctx.risk_score:.4f}",
            f"Determined risk level: {ctx.risk_level}",
        ]
        if ctx.risk_breakdown and ctx.risk_breakdown.hallucination_boost > 0:
            actions.append(
                f"Applied hallucination boost: +{ctx.risk_breakdown.hallucination_boost:.4f}"
            )
        return actions

    @staticmethod
    def _generator_actions(ctx: PipelineContext) -> List[str]:
        meta = ctx.metadata.get("safe_response_metadata", {})
        mods: List[str] = meta.get("modifications_made", [])
        actions: List[str] = []
        if mods:
            actions.append(f"Modified response with {len(mods)} change(s)")
            for mod in mods[:5]:  # cap to avoid huge lists
                actions.append(f"  • {mod}")
        else:
            actions.append("Response passed through without modification")
        return actions

    @staticmethod
    def _evaluator_actions(ctx: PipelineContext) -> List[str]:
        report = ctx.evaluation_report
        if report is None:
            return ["Evaluation skipped or failed"]
        result = "PASS" if report.passed else "FAIL"
        return [
            f"Evaluated pipeline output: {result} ({report.overall_score:.1f}/100)",
            f"Coverage={report.coverage_score:.0f} Consistency={report.consistency_score:.0f} "
            f"RiskConsistency={report.risk_consistency_score:.0f} Safety={report.safety_score:.0f}",
        ]

    @staticmethod
    def _memory_actions(ctx: PipelineContext) -> List[str]:
        saved = ctx.metadata.get("memory_saved", False)
        sid = ctx.metadata.get("session_id", "N/A")
        if saved:
            return [f"Persisted session {sid}"]
        return ["Session persistence skipped or failed"]

    @staticmethod
    def _alert_actions(ctx: PipelineContext) -> List[str]:
        if ctx.alerts:
            return [f"Triggered {len(ctx.alerts)} alert(s)"]
        return ["No alerts triggered"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_iso(ts: str) -> datetime:
        """Parse an ISO-8601 string, defaulting to UTC on failure."""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)
