"""
severity_calculator.py
----------------------
Maps symptom/query text to a clinical severity score (0.0 – 1.0).

Rules
-----
chest pain            → 0.90
heart attack          → 1.00
stroke                → 1.00
breathing difficulty  → 0.95
shortness of breath   → 0.95
unconscious           → 1.00
default               → 0.30
"""

from __future__ import annotations

import logging
import re
import time

logger = logging.getLogger("clinguard.observability")

# ---------------------------------------------------------------------------
# Keyword → severity mapping (ordered: highest priority first)
# ---------------------------------------------------------------------------
_SEVERITY_RULES: list[tuple[list[str], float]] = [
    (["heart attack", "myocardial infarction", "cardiac arrest"], 1.00),
    (["stroke", "cerebrovascular accident", "cva"], 1.00),
    (["unconscious", "unresponsive", "loss of consciousness", "syncope"], 1.00),
    (["breathing difficulty", "respiratory distress", "respiratory failure"], 0.95),
    (["shortness of breath", "dyspnea", "can't breathe", "cannot breathe"], 0.95),
    (["chest pain", "chest tightness", "chest pressure", "chest discomfort"], 0.90),
    (["severe bleeding", "hemorrhage", "anaphylaxis", "anaphylactic"], 0.90),
    (["seizure", "convulsion", "epileptic"], 0.85),
    (["sepsis", "septic shock", "blood poisoning"], 0.85),
    (["severe pain", "extreme pain"], 0.75),
    (["high fever", "fever above 104", "hyperthermia"], 0.70),
    (["fracture", "broken bone", "dislocation"], 0.65),
    (["infection", "inflammation"], 0.55),
    (["headache", "nausea", "vomiting", "dizziness", "fatigue"], 0.45),
    (["mild pain", "slight discomfort", "minor"], 0.35),
]

_DEFAULT_SEVERITY: float = 0.30


class SeverityCalculator:
    """
    Stateless calculator that scores clinical severity from free text.

    Usage
    -----
    >>> sc = SeverityCalculator()
    >>> sc.calculate("Patient presents with chest pain and shortness of breath.")
    0.95
    """

    def calculate(self, text: str) -> float:
        """
        Return the highest severity score for any keyword found in *text*.

        Parameters
        ----------
        text : str
            Combined query + ai_response text to evaluate.

        Returns
        -------
        float
            Severity score in [0.0, 1.0].
        """
        start = time.perf_counter()
        logger.info("[SeverityCalculator] started")

        normalised = text.lower()
        best_score = _DEFAULT_SEVERITY

        for keywords, score in _SEVERITY_RULES:
            for kw in keywords:
                pattern = re.compile(r"\b" + re.escape(kw) + r"\b")
                if pattern.search(normalised):
                    if score > best_score:
                        best_score = score
                        logger.info(
                            f"[SeverityCalculator] matched keyword='{kw}' score={score}"
                        )
                    # Once we hit the highest possible score, stop searching
                    if best_score == 1.0:
                        break
            if best_score == 1.0:
                break

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            f"[SeverityCalculator] completed "
            f"severity={best_score:.3f} time={elapsed:.2f}ms"
        )
        return best_score
