"""
urgency_calculator.py
---------------------
Categorises symptom text into urgency bands and returns an urgency score.

Rules
-----
emergency symptoms  → 0.90
serious symptoms    → 0.70
routine symptoms    → 0.30
default             → 0.30
"""

from __future__ import annotations

import logging
import re
import time

logger = logging.getLogger("clinguard.observability")

# ---------------------------------------------------------------------------
# Symptom category keyword sets
# ---------------------------------------------------------------------------
_EMERGENCY_KEYWORDS: list[str] = [
    "chest pain",
    "heart attack",
    "myocardial infarction",
    "cardiac arrest",
    "stroke",
    "cerebrovascular accident",
    "unconscious",
    "unresponsive",
    "loss of consciousness",
    "syncope",
    "breathing difficulty",
    "shortness of breath",
    "dyspnea",
    "can't breathe",
    "cannot breathe",
    "respiratory failure",
    "respiratory distress",
    "anaphylaxis",
    "anaphylactic",
    "severe bleeding",
    "hemorrhage",
    "septic shock",
    "sepsis",
    "overdose",
    "poisoning",
    "choking",
    "drowning",
    "severe allergic reaction",
]

_SERIOUS_KEYWORDS: list[str] = [
    "seizure",
    "convulsion",
    "high fever",
    "fever above 103",
    "fever above 104",
    "severe pain",
    "extreme pain",
    "fracture",
    "broken bone",
    "dislocation",
    "infection spreading",
    "wound infection",
    "deep laceration",
    "internal bleeding",
    "hypertensive crisis",
    "diabetic emergency",
    "hypoglycemia",
    "hyperglycemia",
    "acute appendicitis",
    "kidney stone",
    "severe migraine",
    "vision loss",
    "sudden weakness",
    "sudden numbness",
    "confusion",
    "altered mental status",
]

_ROUTINE_KEYWORDS: list[str] = [
    "headache",
    "mild pain",
    "slight discomfort",
    "common cold",
    "runny nose",
    "sore throat",
    "minor cut",
    "bruise",
    "muscle ache",
    "fatigue",
    "nausea",
    "mild fever",
    "low-grade fever",
    "diarrhea",
    "constipation",
    "indigestion",
    "rash",
    "itching",
    "dry skin",
    "minor sprain",
]

_URGENCY_SCORES: dict[str, float] = {
    "emergency": 0.90,
    "serious": 0.70,
    "routine": 0.30,
}
_DEFAULT_URGENCY: float = 0.30


def _match_any(text: str, keywords: list[str]) -> bool:
    for kw in keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            return True
    return False


class UrgencyCalculator:
    """
    Stateless urgency scorer based on symptom category classification.

    Usage
    -----
    >>> uc = UrgencyCalculator()
    >>> uc.calculate("patient has chest pain and cannot breathe")
    0.9
    """

    def calculate(self, text: str) -> float:
        """
        Return urgency score for *text*.

        Evaluation order: emergency → serious → routine → default.

        Parameters
        ----------
        text : str
            Combined query + ai_response text.

        Returns
        -------
        float
            Urgency score in [0.0, 1.0].
        """
        start = time.perf_counter()
        logger.info("[UrgencyCalculator] started")

        normalised = text.lower()

        if _match_any(normalised, _EMERGENCY_KEYWORDS):
            category = "emergency"
        elif _match_any(normalised, _SERIOUS_KEYWORDS):
            category = "serious"
        elif _match_any(normalised, _ROUTINE_KEYWORDS):
            category = "routine"
        else:
            category = "default"

        score = _URGENCY_SCORES.get(category, _DEFAULT_URGENCY)

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            f"[UrgencyCalculator] completed "
            f"category={category} urgency={score:.3f} time={elapsed:.2f}ms"
        )
        return score
