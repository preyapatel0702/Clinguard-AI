"""
generator.py
------------
Phase 5 — Intelligent Safe Response Generator

Produces a clinically safe version of an AI response by:
1. Removing entire dangerous-advice sentences (stay home, rest at home, wait a few days…)
2. Erasing invalid claim terms (fake diseases / drugs from ValidatorAgent)
3. Applying pattern-based dangerous clause replacement
4. Replacing unsafe clauses with evidence-based safe alternatives
5. Preserving genuinely useful information
6. Appending a mandatory safety disclaimer
7. Returning a confidence score and full modification log

This module is intentionally free of external model calls — all replacements
are deterministic rule-based transformations, making the system reliable and
free of latency from API calls.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

from backend.models.schemas import (
    HallucinationResult,
    SafeResponseMetadata,
    ValidationResult,
)

logger = logging.getLogger("clinguard.observability")

# ---------------------------------------------------------------------------
# Safety disclaimer (appended to every response)
# ---------------------------------------------------------------------------
_DISCLAIMER = (
    "\n\n⚠️ IMPORTANT: This information is AI-generated and may not be accurate. "
    "Always consult a licensed healthcare professional before making any medical decisions. "
    "Do not start, stop, or modify medications or treatments based solely on AI-generated advice."
)

# ---------------------------------------------------------------------------
# Emergency redirect message
# ---------------------------------------------------------------------------
_EMERGENCY_REDIRECT = (
    "⚠️ MEDICAL EMERGENCY POSSIBLE: This symptom may indicate a serious or life-threatening condition. "
    "Seek immediate medical evaluation. "
    "Call emergency services (e.g., 911 / 112 / 999) if symptoms are severe or worsening."
)

# ---------------------------------------------------------------------------
# Dangerous pattern rules
# Each rule: (regex_pattern, safe_replacement, modification_label)
# ---------------------------------------------------------------------------
_DANGER_RULES: list[tuple[str, str, str]] = [
    # Home treatment for serious symptoms
    (
        r"\bchest\s+pain\b.{0,80}?\btreated?\s+at\s+home\b",
        "Chest pain may indicate a medical emergency. "
        "Seek immediate medical evaluation. "
        "Call emergency services if symptoms are severe.",
        "Replaced home-treatment advice for chest pain with emergency guidance",
    ),
    (
        r"\btreated?\s+at\s+home\b.{0,80}?\bchest\s+pain\b",
        "Chest pain requires prompt medical evaluation. "
        "Do not attempt to manage chest pain at home without professional guidance.",
        "Replaced home-treatment advice for chest pain with emergency guidance",
    ),
    (
        r"\bstroke\b.{0,80}?\btreated?\s+at\s+home\b",
        "Stroke is a medical emergency. "
        "Call emergency services immediately. "
        "Do not attempt home treatment.",
        "Replaced home-treatment advice for stroke with emergency guidance",
    ),
    (
        r"\btreated?\s+at\s+home\b.{0,80}?\bstroke\b",
        "Stroke symptoms require immediate emergency care. "
        "Call 911 or your local emergency number now.",
        "Replaced home-treatment advice for stroke with emergency guidance",
    ),
    # Dangerous combination medications
    (
        r"\bibuprofen[\s\-]+metformin\b",
        "[UNSAFE COMBINATION REMOVED — consult a pharmacist or physician for safe medication options]",
        "Removed ibuprofen-metformin combination (contraindicated)",
    ),
    (
        r"\btake\s+\w+\s+and\s+\w+\s+(?:together|simultaneously|at the same time)\b",
        "[Medication combination guidance removed — consult a licensed pharmacist before combining medications]",
        "Removed unverified medication combination advice",
    ),
    # Symptom minimisation for serious conditions
    (
        r"\b(?:chest\s+pain|heart\s+attack|stroke|breathing\s+difficulty)\b.{0,60}?\b(?:not\s+serious|nothing\s+to\s+worry|harmless|minor|benign)\b",
        "This symptom should be evaluated by a medical professional. "
        "It is not safe to dismiss these symptoms without a clinical assessment.",
        "Replaced symptom minimisation for serious condition",
    ),
    (
        r"\b(?:not\s+serious|nothing\s+to\s+worry|harmless)\b.{0,60}?\b(?:chest\s+pain|heart\s+attack|stroke)\b",
        "These symptoms require professional medical evaluation and should not be dismissed.",
        "Replaced symptom minimisation for serious condition",
    ),
    # Unsafe dosage instructions
    (
        r"\btake\s+(?:\d+\s+)?(?:mg|milligrams?|tablets?|capsules?|pills?|doses?)\s+(?:every\s+\d+\s+hours?|(?:twice|three\s+times?)\s+daily)\b.{0,120}?\bwithout\s+(?:consulting|seeing|talking\s+to)\b",
        "[Dosage instruction removed — do not follow dosage guidance without consulting a healthcare professional]",
        "Removed unverified self-dosage instructions",
    ),
    # Dangerous self-diagnosis instructions
    (
        r"\byou\s+(?:have|have\s+a|are\s+suffering\s+from)\s+(?:cancer|tumou?r|leukemia|lymphoma|aids|hiv)\b",
        "[Diagnosis removed — AI cannot diagnose medical conditions. Consult a physician for accurate diagnosis.]",
        "Removed AI self-diagnosis of serious condition",
    ),
    # Advising to ignore symptoms
    (
        r"\b(?:ignore|dismiss|don't\s+worry\s+about|do\s+not\s+worry\s+about)\b.{0,60}?\b(?:chest\s+pain|breathing|stroke|pain|symptoms?)\b",
        "Do not ignore medical symptoms. Seek medical evaluation if you are experiencing persistent or worsening symptoms.",
        "Replaced advice to ignore symptoms with safety guidance",
    ),
    # Delay in seeking care
    (
        r"\bwait\s+(?:a\s+few\s+days?|a\s+week|several\s+days?|some\s+time)\b.{0,60}?\b(?:chest\s+pain|breathing|stroke|emergency)\b",
        "Do not delay seeking medical care for serious symptoms. Contact a healthcare professional immediately.",
        "Replaced delayed care advice for serious symptom",
    ),
]

# ---------------------------------------------------------------------------
# Issue 3 — Dangerous-advice sentence patterns
# Entire sentences matching these patterns are removed and replaced.
# Each entry: (compiled regex, replacement text, label)
# ---------------------------------------------------------------------------
_DANGEROUS_ADVICE_SENTENCE_RULES: list[tuple[re.Pattern, str, str]] = [
    (
        re.compile(
            r"[^.!?]*\b(?:stay\s+home|stay\s+at\s+home)\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Seek immediate medical evaluation if symptoms are severe or worsening. "
        "Do not delay contacting a healthcare professional.",
        "Removed 'stay home' dangerous advice",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:rest\s+at\s+home|resting\s+at\s+home)\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Please consult a licensed healthcare professional before deciding on a course of action.",
        "Removed 'rest at home' dangerous advice",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:wait\s+(?:two|2|a\s+few|several|some)\s+days?|wait\s+a\s+week)\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Do not delay seeking medical care. Contact a healthcare professional promptly.",
        "Removed 'wait a few days' dangerous advice",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:ignore\s+(?:the\s+)?(?:your\s+)?symptoms?|do\s+nothing\s+about\s+it)\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Do not ignore medical symptoms. Seek medical evaluation for any persistent or worsening symptoms.",
        "Removed 'ignore symptoms' dangerous advice",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:no\s+need\s+to\s+see\s+a\s+doctor|you\s+don'?t\s+need\s+(?:to\s+see\s+a\s+doctor|medical\s+attention))\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Please consult a licensed healthcare professional for an accurate evaluation.",
        "Removed 'no need to see a doctor' dangerous advice",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:symptoms?\s+(?:are|is)\s+not\s+serious|not\s+(?:a\s+)?serious\s+(?:condition|symptom|concern))\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Any persistent or concerning symptoms should be evaluated by a medical professional.",
        "Removed symptom minimisation sentence",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:drink|consume)\s+bleach\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Bleach is poisonous and must never be consumed. Seek immediate medical attention if ingestion has occurred.",
        "Removed bleach ingestion advice",
    ),
    (
        re.compile(
            r"[^.!?]*\bdrink\s+disinfectant\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Disinfectants are toxic and should never be ingested. Contact emergency medical services immediately if swallowed.",
        "Removed disinfectant ingestion advice",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:kerosene|gasoline|turpentine)\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Petroleum products are poisonous and must never be ingested. Seek emergency medical care immediately.",
        "Removed toxic ingestion advice",
    ),
    (
        re.compile(
            r"[^.!?]*\bstop\s+insulin\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Do not stop insulin without guidance from your treating physician.",
        "Removed dangerous insulin advice",
    ),
    (
        re.compile(
            r"[^.!?]*\bskip\s+chemotherapy\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "Do not stop or delay chemotherapy without consulting your oncology team.",
        "Removed chemotherapy advice",
    ),
    (
        re.compile(
            r"[^.!?]*\b(?:cures\s+cancer|guaranteed\s+cure|miracle\s+cure|100%\s+cure)\b[^.!?]*[.!?]",
            re.IGNORECASE,
        ),
        "No treatment can be guaranteed to cure serious diseases. Treatment decisions should always be based on medical evidence.",
        "Removed unsupported cure claim",
    )
]

# Replacement wording for invalid disease claims (Issue 1)
_INVALID_DISEASE_REPLACEMENT = (
    "The condition mentioned could not be verified using trusted medical references. "
    "Please consult a licensed healthcare professional for further evaluation."
)

# Replacement wording for invalid drug/medication claims (Issue 1)
_INVALID_DRUG_REPLACEMENT = (
    "The medication mentioned could not be verified using trusted medical references. "
    "Consult a physician or pharmacist before taking any medication."
)

# ---------------------------------------------------------------------------
# Risk level → preamble map
# ---------------------------------------------------------------------------
_RISK_PREAMBLE: dict[str, str] = {
    "CRITICAL": (
        "⛔ CRITICAL RISK DETECTED: The following response contained potentially dangerous medical information. "
        "A safety review has been applied.\n\n"
    ),
    "HIGH": (
        "⚠️ HIGH RISK: The AI response contained information that may pose patient safety risks. "
        "Content has been reviewed and modified for safety.\n\n"
    ),
    "MODERATE": (
        "ℹ️ MODERATE RISK: Some medical claims in the AI response could not be fully verified. "
        "Please review with a qualified professional.\n\n"
    ),
    "LOW": "",
}

_HALLUCINATION_NOTICE = (
    "\n\n🔴 Potentially unsafe medical information detected. "
    "Please consult a licensed healthcare professional. "
    "Do not start, stop, or modify medications based solely on AI-generated advice."
)


class SafeResponseGenerator:
    """
    Intelligent safe response generator.

    Transforms a raw AI medical response into a clinically safe response by:
    - Applying pattern-based dangerous clause replacement
    - Inserting contextual emergency guidance where needed
    - Adding hallucination notices when fake drugs/diseases are detected
    - Preserving genuinely safe information
    - Attaching a mandatory disclaimer

    Usage
    -----
    >>> gen = SafeResponseGenerator()
    >>> meta = gen.generate(
    ...     original="Chest pain can be treated at home.",
    ...     hallucinations=[],
    ...     risk_level="CRITICAL",
    ...     validations=[],
    ... )
    >>> print(meta.safe_response)
    """

    def generate(
        self,
        original: str,
        hallucinations: list[HallucinationResult],
        risk_level: str,
        validations: list[ValidationResult],
    ) -> SafeResponseMetadata:
        """
        Generate a safe response from raw AI output.

        Parameters
        ----------
        original : str
            Raw AI response to process.
        hallucinations : list[HallucinationResult]
            Detected hallucinations from DetectorAgent.
        risk_level : str
            Risk level from RiskAgent (LOW/MODERATE/HIGH/CRITICAL).
        validations : list[ValidationResult]
            Validation results from ValidatorAgent.

        Returns
        -------
        SafeResponseMetadata
            Rich metadata including safe_response, safety_reason, confidence.
        """
        start = time.perf_counter()
        logger.info("[SafeResponseGenerator] started")

        modifications: list[str] = []
        working_text = original

        # --------------------------------------------------------------------
        # Step 1 (Issue 3): Remove entire dangerous-advice sentences
        # Runs BEFORE pattern rules so the dangerous text is fully gone
        # --------------------------------------------------------------------
        for compiled_pattern, replacement, label in _DANGEROUS_ADVICE_SENTENCE_RULES:
            new_text, count = compiled_pattern.subn(replacement + " ", working_text)
            if count > 0:
                modifications.append(label)
                working_text = new_text.strip()
                logger.info(f"[SafeResponseGenerator] sentence rule: {label}")

        # --------------------------------------------------------------------
        # Step 2 (Issue 1): Erase invalid claim terms from ValidatorAgent
        # For every is_valid=False result, scrub the claim text from the
        # response and replace with appropriate neutral safe wording.
        # --------------------------------------------------------------------
        invalid_validations = [v for v in validations if not v.is_valid]
        has_fake_drug = False
        has_fake_disease = False
        active_hallucinations = [h for h in hallucinations if h.is_hallucination]

        for validation in invalid_validations:
            term = (validation.claim_text or "").strip()
            if not term:
                continue

            detected = term
            detected_lower = detected.lower()
            details_lower = ""

            # Attempt to use a matching hallucination for context if available
            matching_hallucination = next(
                (
                    h
                    for h in active_hallucinations
                    if h.detected_text and h.detected_text.strip().lower() == detected_lower
                ),
                None,
            )
            if matching_hallucination:
                details_lower = matching_hallucination.details.lower()

            is_drug = (
                any(kw in details_lower for kw in ["drug", "medication", "medicine", "pharmaceutical"])
                or any(kw in detected_lower for kw in ["mg", "tablet", "capsule", "dose", "pill", "syrup"])
                or any(kw in detected_lower for kw in ["ibuprofen", "metformin", "aspirin", "acetaminophen", "penicillin"])
            )
            is_disease = (
                any(kw in details_lower for kw in ["disease", "condition", "diagnosis", "syndrome"])
                or any(kw in detected_lower for kw in ["disease", "syndrome", "disorder", "condition", "infection", "cancer", "fever", "hypertension", "asthma", "diabetes"])
            )

            if is_drug:
                has_fake_drug = True
                replacement_text = _INVALID_DRUG_REPLACEMENT
                label = f"Erased invalid drug claim: '{detected}'"
            elif is_disease:
                has_fake_disease = True
                replacement_text = _INVALID_DISEASE_REPLACEMENT
                label = f"Erased invalid disease claim: '{detected}'"
            else:
                replacement_text = _INVALID_DISEASE_REPLACEMENT
                label = f"Erased invalid medical claim: '{detected}'"

            sentence_pattern = re.compile(
                r"[^.!?\n]*" + re.escape(detected) + r"[^.!?\n]*[.!?]",
                re.IGNORECASE,
            )
            new_text, count = sentence_pattern.subn(replacement_text + " ", working_text)
            if count > 0:
                working_text = new_text.strip()
                modifications.append(label)
                logger.info(f"[SafeResponseGenerator] {label}")
                continue

            # Fallback: remove the term directly if sentence boundaries are not found
            term_pattern = re.compile(re.escape(detected), re.IGNORECASE)
            new_text, count = term_pattern.subn(replacement_text + " ", working_text)
            if count > 0:
                working_text = new_text
                modifications.append(label + " (term-level)")
                logger.info(f"[SafeResponseGenerator] {label} (term-level)")

        # --------------------------------------------------------------------
        # Step 3: Apply dangerous pattern replacements
        # --------------------------------------------------------------------
        for pattern, replacement, label in _DANGER_RULES:
            new_text, count = re.subn(
                pattern,
                replacement,
                working_text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if count > 0:
                modifications.append(label)
                working_text = new_text
                logger.info(f"[SafeResponseGenerator] applied rule: {label}")

        # --------------------------------------------------------------------
        # Step 3b: Final dangerous advice cleanup
        # Ensure no listed dangerous advice phrase remains in the final response.
        # --------------------------------------------------------------------
        dangerous_phrases = [
            "stay home",
            "rest at home",
            "wait two days",
            "wait a few days",
            "ignore symptoms",
            "do nothing",
            "no need to see a doctor",
            "symptoms are not serious",
            "drink bleach",
            "consume bleach",
            "drink disinfectant",
            "kerosene",
            "gasoline",
            "turpentine",
            "stop insulin",
            "skip chemotherapy",
            "cures cancer",
            "guaranteed cure",
        ]
        cleanup_pattern = re.compile(
            r"[^.!?]*\b(?:" + "|".join(re.escape(phrase) for phrase in dangerous_phrases) + r")\b[^.!?]*[.!?]",
            re.IGNORECASE,
        )
        cleanup_replacement = (
            "If you are experiencing concerning symptoms, seek immediate medical evaluation. "
            "Do not delay contacting a licensed healthcare professional."
        )
        new_text, count = cleanup_pattern.subn(cleanup_replacement + " ", working_text)
        if count > 0:
            modifications.append("Removed remaining dangerous advice phrase(s)")
            working_text = new_text.strip()
            logger.info("[SafeResponseGenerator] Removed remaining dangerous advice phrase(s)")

        # --------------------------------------------------------------------
        # Step 4: Handle hallucinated content notices
        # --------------------------------------------------------------------
        if active_hallucinations:
            working_text += (
                "\n\n"
                "The original AI response contained medical information that could not "
                "be verified against trusted clinical references. Unsafe content has "
                "been removed or replaced with safer guidance."
            )
            modifications.append(
                f"Appended hallucination warning ({len(active_hallucinations)} hallucination(s) detected)"
            )

        # --------------------------------------------------------------------
        # 3. Add emergency redirect for CRITICAL/HIGH risk
        # --------------------------------------------------------------------
        if risk_level in ("CRITICAL", "HIGH"):
            working_text = _EMERGENCY_REDIRECT + "\n\n" + working_text
            modifications.append(f"Prepended emergency redirect for risk_level={risk_level}")

        # --------------------------------------------------------------------
        # 4. Prepend risk-level preamble
        # --------------------------------------------------------------------
        preamble = _RISK_PREAMBLE.get(risk_level, "")
        if preamble:
            working_text = preamble + working_text
            modifications.append(f"Prepended {risk_level} risk preamble")

        # --------------------------------------------------------------------
        # 5. Always append mandatory disclaimer
        # --------------------------------------------------------------------
        working_text += _DISCLAIMER
        modifications.append("Appended mandatory safety disclaimer")

        # --------------------------------------------------------------------
        # 6. Compute confidence score
        # --------------------------------------------------------------------
        confidence = _compute_confidence(
            original=original,
            modifications=modifications,
            risk_level=risk_level,
            has_fake_drug=has_fake_drug,
            has_fake_disease=has_fake_disease,
            num_hallucinations=len(active_hallucinations),
        )

        # --------------------------------------------------------------------
        # 7. Build safety_reason summary
        # --------------------------------------------------------------------
        if modifications:
            safety_reason = (
                f"{len(modifications)} safety modification(s) applied: "
                + "; ".join(modifications[:5])
                + ("..." if len(modifications) > 5 else "")
            )
        else:
            safety_reason = "No dangerous patterns detected. Response passed safety review."

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            f"[SafeResponseGenerator] completed modifications={len(modifications)} "
            f"confidence={confidence:.3f} time={elapsed:.2f}ms"
        )

        return SafeResponseMetadata(
            original_response=original,
            safe_response=working_text,
            safety_reason=safety_reason,
            confidence=round(confidence, 4),
            modifications_made=modifications,
        )


def _compute_confidence(
    original: str,
    modifications: list[str],
    risk_level: str,
    has_fake_drug: bool,
    has_fake_disease: bool,
    num_hallucinations: int,
) -> float:
    """
    Confidence reflects how well the generator handled the response.
    Higher confidence = more dangerous content was caught and replaced.

    Base: 0.90
    Penalty for unhandled high risk:
      - HIGH/CRITICAL with no modifications to core content: -0.10
    Boost for each active modification (capped):
      - each substantive modification: +0.02 (up to +0.10)
    Penalty per hallucination not caught by rules: -0.05 per (up to -0.20)
    """
    base = 0.95

    # Boost for substantive modifications (not counting preamble/disclaimer)
    substantive = [m for m in modifications if "disclaimer" not in m and "preamble" not in m]
    boost = min(len(substantive) * 0.02, 0.10)

    # Penalise unresolved hallucinations (up to -0.20)
    unresolved_penalty = min(num_hallucinations * 0.05, 0.20)

    # Penalise fake drug/disease without core-content modification
    if has_fake_drug and not any("drug" in m.lower() or "medication" in m.lower() for m in modifications):
        unresolved_penalty += 0.05
    if has_fake_disease and not any("disease" in m.lower() or "diagnosis" in m.lower() for m in modifications):
        unresolved_penalty += 0.05

    confidence = min(1.0, max(0.0, base + boost - unresolved_penalty))
    return confidence
