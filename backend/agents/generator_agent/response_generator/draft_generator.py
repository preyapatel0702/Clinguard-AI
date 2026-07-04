"""
draft_generator.py
-------------------
Draft (raw) clinical response generation.

Root-cause fix
--------------
``POST /chat/messages`` previously built its ``AnalyzeRequest`` with
``ai_response=text`` — i.e. it fed the *user's own question* back into the
pipeline as if it were the AI's answer. Because the "answer" contained no
dangerous phrases, SafeResponseGenerator had nothing to rewrite, so the
final safe_response was just the question plus the mandatory disclaimer.

The pipeline's job (GeneratorAgent / SafeResponseGenerator) is to take an
*already-generated* raw AI response and make it safe — it is not, and
should not become, responsible for drafting the initial clinical content.
That drafting step belongs upstream of the pipeline. This module supplies
that missing step: a small, deterministic "prompt template" based
responder that stands in for an LLM call and produces genuine clinical
guidance text for a user's query. Its output is then handed to the
existing, unmodified ClinGuardPipeline (DetectorAgent, ValidatorAgent,
RiskAgent, GeneratorAgent, ...) exactly as before, so all existing safety
behavior (dangerous-pattern scrubbing, risk-based preambles, the
emergency-response override for HIGH/CRITICAL, and the mandatory
disclaimer) is fully preserved.

This is intentionally rule-based/deterministic (no external API calls),
consistent with the rest of the pipeline's safety-generation code.
"""

from __future__ import annotations

import re
from typing import NamedTuple

__all__ = ["DraftResponseGenerator"]


class _Template(NamedTuple):
    keywords: tuple[str, ...]
    response: str


# ---------------------------------------------------------------------------
# Prompt templates
# Keyword-triggered, generically-safe clinical guidance. These are drafts
# only: they are still passed through the full safety pipeline afterward,
# which adds risk-based preambles/disclaimers and can override them
# entirely for HIGH/CRITICAL risk queries.
# ---------------------------------------------------------------------------
_TEMPLATES: tuple[_Template, ...] = (
    _Template(
        ("headache", "migraine"),
        "Mild headaches, especially after studying or screen time, are often "
        "related to eye strain, dehydration, poor posture, or tension. "
        "Taking a short break, resting your eyes, stretching your neck and "
        "shoulders, drinking water, and resting in a quiet, dimly lit room "
        "can often help. Over-the-counter pain relief may be considered "
        "according to the product label if needed. If the headache is "
        "severe, sudden, worsening, or accompanied by other symptoms such "
        "as vision changes, confusion, or a stiff neck, it should be "
        "evaluated by a healthcare professional.",
    ),
    _Template(
        ("fever", "temperature"),
        "A mild fever is often the body's normal response to a minor "
        "infection. Resting, drinking plenty of fluids, dressing lightly, "
        "and monitoring your temperature can help. Fever-reducing "
        "medication may be considered according to the product label if "
        "needed. If the fever is high, persistent for more than a couple "
        "of days, or accompanied by symptoms such as difficulty breathing, "
        "confusion, or a rash, please seek medical evaluation.",
    ),
    _Template(
        ("cough", "cold", "sore throat", "congestion", "runny nose"),
        "Common cold symptoms such as a cough, sore throat, or congestion "
        "usually improve on their own within a week or two. Staying "
        "hydrated, resting, using a humidifier, and warm fluids like tea "
        "with honey can help ease symptoms. If symptoms last longer than "
        "10 days, worsen significantly, or are accompanied by high fever "
        "or difficulty breathing, please consult a healthcare professional.",
    ),
    _Template(
        ("stomach", "nausea", "vomiting", "diarrhea", "indigestion"),
        "Mild stomach upset, nausea, or indigestion can often be managed "
        "with rest, small sips of water or electrolyte drinks, and bland "
        "foods once you feel able to eat. Avoiding fatty, spicy, or heavy "
        "foods while recovering may help. If symptoms are severe, persist "
        "for more than a couple of days, or are accompanied by signs of "
        "dehydration or blood, please seek medical evaluation.",
    ),
    _Template(
        ("back pain", "muscle pain", "sore muscles", "joint pain"),
        "Mild muscle or joint discomfort is often related to strain, "
        "posture, or overuse. Gentle stretching, rest, alternating heat "
        "and cold, and maintaining good posture can help. If the pain is "
        "severe, does not improve after a few days, or is accompanied by "
        "numbness, weakness, or loss of function, a healthcare "
        "professional should evaluate it.",
    ),
    _Template(
        ("stress", "anxious", "anxiety", "trouble sleeping", "insomnia", "can't sleep"),
        "Occasional stress or difficulty sleeping is common and can often "
        "be helped by a consistent sleep schedule, reducing screen time "
        "before bed, light exercise, and relaxation techniques such as "
        "deep breathing. If stress, anxiety, or sleep difficulties are "
        "persistent or affecting daily life, speaking with a healthcare "
        "professional or counselor is recommended.",
    ),
    _Template(
        ("rash", "itchy skin", "skin irritation", "hives"),
        "Minor skin irritation or a mild rash can sometimes result from "
        "contact with an irritant, dry skin, or a minor allergic reaction. "
        "Keeping the area clean and dry, avoiding known irritants, and "
        "using a gentle moisturizer may help. If the rash spreads rapidly, "
        "is painful, blistering, or accompanied by swelling or difficulty "
        "breathing, seek medical attention promptly.",
    ),
    _Template(
        ("cut", "scrape", "minor injury", "bruise"),
        "For minor cuts, scrapes, or bruises, clean the area gently with "
        "water, apply an antiseptic if available, and cover with a clean "
        "bandage. Applying a cold pack can help reduce swelling from "
        "bruising. If the wound is deep, won't stop bleeding, shows signs "
        "of infection, or you're unsure about the severity, please seek "
        "medical evaluation.",
    ),
)

_FALLBACK_RESPONSE = (
    "Thank you for sharing your symptoms. General self-care such as rest, "
    "staying hydrated, and monitoring how you feel can be helpful for many "
    "minor, everyday complaints. Because every individual's health "
    "situation is different, a licensed healthcare professional is best "
    "placed to give guidance specific to your symptoms, medical history, "
    "and any medications you take. If your symptoms are severe, worsening, "
    "or concerning to you, please seek medical evaluation."
)


class DraftResponseGenerator:
    """
    Deterministic, prompt-template-driven draft response generator.

    Given a raw user query, returns a clinically-oriented draft answer.
    This stands in for an upstream "LLM call" that produces the initial
    (not-yet-safety-reviewed) AI response; the existing ClinGuardPipeline
    remains solely responsible for safety review of that draft.
    """

    def generate(self, query: str) -> str:
        normalized = (query or "").lower()

        for template in _TEMPLATES:
            if any(self._contains(normalized, kw) for kw in template.keywords):
                return template.response

        return _FALLBACK_RESPONSE

    @staticmethod
    def _contains(text: str, keyword: str) -> bool:
        if " " in keyword:
            return keyword in text
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
