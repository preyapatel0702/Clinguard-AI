"""
decision_trace_engine.py
------------------------
Phase 9 — Granular Decision Trace Generator

Inspects PipelineContext to emit one ``DecisionTrace`` object per
*individual decision* made by a pipeline agent.  Examples:

  DetectorAgent
    • extracted_medication
    • extracted_disease
    • hallucination_detected

  ValidatorAgent
    • validated_claim
    • rejected_claim

  RiskAgent
    • calculated_severity
    • determined_risk_level

  GeneratorAgent
    • modified_response
    • inserted_disclaimer
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.models.audit import DecisionTrace
from backend.models.schemas import PipelineContext

logger = logging.getLogger("clinguard.phase9.decision_trace")


class DecisionTraceEngine:
    """Emit granular per-decision trace objects from a completed PipelineContext."""

    def generate(self, context: PipelineContext) -> List[DecisionTrace]:
        """Return all decision traces for the pipeline run."""
        logger.info(
            "decision_trace_engine.generate started patient_id=%s",
            context.patient_id,
        )
        traces: List[DecisionTrace] = []
        traces.extend(self._detector_decisions(context))
        traces.extend(self._validator_decisions(context))
        traces.extend(self._risk_decisions(context))
        traces.extend(self._generator_decisions(context))
        traces.extend(self._evaluator_decisions(context))
        traces.extend(self._memory_decisions(context))
        traces.extend(self._alert_decisions(context))
        logger.info(
            "decision_trace_engine.generate completed count=%d",
            len(traces),
        )
        return traces

    # ------------------------------------------------------------------
    # DetectorAgent decisions
    # ------------------------------------------------------------------

    def _detector_decisions(self, ctx: PipelineContext) -> List[DecisionTrace]:
        decisions: List[DecisionTrace] = []
        timestamp = self._agent_timestamp("DetectorAgent", ctx)

        # Entity extractions
        for category in ("drugs", "diseases", "symptoms"):
            for entity in ctx.medical_entities.get(category, []):
                entity_text = str(entity.get("text", ""))
                entity_score = float(entity.get("score", 0.0))
                action_map = {
                    "drugs": "extracted_medication",
                    "diseases": "extracted_disease",
                    "symptoms": "extracted_symptom",
                }
                decisions.append(
                    DecisionTrace(
                        agent_name="DetectorAgent",
                        action=action_map[category],
                        evidence=[
                            f"Entity: {entity_text}",
                            f"Label: {entity.get('label', category)}",
                        ],
                        confidence=min(entity_score, 1.0),
                        timestamp=timestamp,
                    )
                )

        # Hallucinations
        for h in ctx.hallucinations:
            if h.is_hallucination:
                decisions.append(
                    DecisionTrace(
                        agent_name="DetectorAgent",
                        action="hallucination_detected",
                        evidence=[
                            f"Text: {h.detected_text}",
                            f"Details: {h.details}",
                        ],
                        confidence=h.confidence_score,
                        timestamp=timestamp,
                    )
                )

        return decisions

    # ------------------------------------------------------------------
    # ValidatorAgent decisions
    # ------------------------------------------------------------------

    def _validator_decisions(self, ctx: PipelineContext) -> List[DecisionTrace]:
        decisions: List[DecisionTrace] = []
        timestamp = self._agent_timestamp("ValidatorAgent", ctx)

        for v in ctx.validations:
            claim_text = v.claim_text or v.claim_id
            action = "validated_claim" if v.is_valid else "rejected_claim"
            decisions.append(
                DecisionTrace(
                    agent_name="ValidatorAgent",
                    action=action,
                    evidence=[
                        f"Claim: {claim_text}",
                        f"Source: {v.source}",
                        f"Reasoning: {v.reasoning}",
                    ],
                    confidence=v.confidence,
                    timestamp=timestamp,
                )
            )

        return decisions

    # ------------------------------------------------------------------
    # RiskAgent decisions
    # ------------------------------------------------------------------

    def _risk_decisions(self, ctx: PipelineContext) -> List[DecisionTrace]:
        decisions: List[DecisionTrace] = []
        timestamp = self._agent_timestamp("RiskAgent", ctx)
        breakdown = ctx.risk_breakdown

        if breakdown:
            decisions.append(
                DecisionTrace(
                    agent_name="RiskAgent",
                    action="calculated_severity",
                    evidence=[
                        f"Severity: {breakdown.severity_score:.4f}",
                        f"Urgency: {breakdown.urgency_score:.4f}",
                        f"Vulnerability: {breakdown.vulnerability_score:.4f}",
                        f"Raw score: {breakdown.raw_score:.4f}",
                    ],
                    confidence=0.95,
                    timestamp=timestamp,
                )
            )

        decisions.append(
            DecisionTrace(
                agent_name="RiskAgent",
                action="determined_risk_level",
                evidence=[
                    f"Risk level: {ctx.risk_level}",
                    f"Risk score: {ctx.risk_score:.4f}",
                ],
                confidence=0.95,
                timestamp=timestamp,
            )
        )

        if breakdown and breakdown.hallucination_boost > 0:
            decisions.append(
                DecisionTrace(
                    agent_name="RiskAgent",
                    action="applied_hallucination_boost",
                    evidence=[
                        f"Boost amount: +{breakdown.hallucination_boost:.4f}",
                        f"Final score: {breakdown.final_score:.4f}",
                    ],
                    confidence=0.95,
                    timestamp=timestamp,
                )
            )

        return decisions

    # ------------------------------------------------------------------
    # GeneratorAgent decisions
    # ------------------------------------------------------------------

    def _generator_decisions(self, ctx: PipelineContext) -> List[DecisionTrace]:
        decisions: List[DecisionTrace] = []
        timestamp = self._agent_timestamp("GeneratorAgent", ctx)
        meta: Dict[str, Any] = ctx.metadata.get("safe_response_metadata", {})
        modifications: List[str] = meta.get("modifications_made", [])

        if modifications:
            decisions.append(
                DecisionTrace(
                    agent_name="GeneratorAgent",
                    action="modified_response",
                    evidence=[f"Modification: {m}" for m in modifications],
                    confidence=meta.get("confidence", 0.9),
                    timestamp=timestamp,
                )
            )

        # Check for disclaimer insertion
        safe_lower = ctx.safe_response.lower()
        if "disclaimer" in safe_lower or "consult" in safe_lower:
            decisions.append(
                DecisionTrace(
                    agent_name="GeneratorAgent",
                    action="inserted_disclaimer",
                    evidence=["Safety disclaimer appended to response"],
                    confidence=1.0,
                    timestamp=timestamp,
                )
            )

        return decisions

    # ------------------------------------------------------------------
    # EvaluatorAgent decisions
    # ------------------------------------------------------------------

    def _evaluator_decisions(self, ctx: PipelineContext) -> List[DecisionTrace]:
        decisions: List[DecisionTrace] = []
        timestamp = self._agent_timestamp("EvaluatorAgent", ctx)

        if ctx.evaluation_report:
            report = ctx.evaluation_report
            result = "PASS" if report.passed else "FAIL"
            decisions.append(
                DecisionTrace(
                    agent_name="EvaluatorAgent",
                    action="evaluated_pipeline",
                    evidence=[
                        f"Result: {result}",
                        f"Overall score: {report.overall_score:.1f}",
                        f"Coverage: {report.coverage_score:.0f}",
                        f"Consistency: {report.consistency_score:.0f}",
                    ],
                    confidence=report.overall_score / 100.0,
                    timestamp=timestamp,
                )
            )

        return decisions

    # ------------------------------------------------------------------
    # MemoryAgent decisions
    # ------------------------------------------------------------------

    def _memory_decisions(self, ctx: PipelineContext) -> List[DecisionTrace]:
        decisions: List[DecisionTrace] = []
        timestamp = self._agent_timestamp("MemoryAgent", ctx)

        saved = ctx.metadata.get("memory_saved", False)
        session_id = ctx.metadata.get("session_id", "N/A")
        if saved:
            decisions.append(
                DecisionTrace(
                    agent_name="MemoryAgent",
                    action="persisted_session",
                    evidence=[f"Session ID: {session_id}"],
                    confidence=1.0,
                    timestamp=timestamp,
                )
            )

        return decisions

    # ------------------------------------------------------------------
    # AlertAgent decisions
    # ------------------------------------------------------------------

    def _alert_decisions(self, ctx: PipelineContext) -> List[DecisionTrace]:
        decisions: List[DecisionTrace] = []
        timestamp = self._agent_timestamp("AlertAgent", ctx)

        for alert in ctx.alerts:
            decisions.append(
                DecisionTrace(
                    agent_name="AlertAgent",
                    action="triggered_alert",
                    evidence=[
                        f"Alert ID: {alert.alert_id}",
                        f"Severity: {alert.severity}",
                        f"Message: {alert.message}",
                    ],
                    confidence=1.0,
                    timestamp=timestamp,
                )
            )

        return decisions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _agent_timestamp(agent_name: str, ctx: PipelineContext) -> str:
        """Return the trace timestamp for *agent_name*, or a fallback."""
        for trace in ctx.traces:
            if trace.agent_name == agent_name:
                return trace.timestamp
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
