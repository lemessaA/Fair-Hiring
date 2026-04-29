"""Sample rubric: software engineer role (weights for aggregator + evaluation hints)."""

from __future__ import annotations

from typing import Any

RUBRIC_ID_SOFTWARE_ENGINEER = "software_engineer_v1"

# Weights used when mapping sub-scores to a single interview score (evaluation engine)
RUBRIC_WEIGHTS: dict[str, float] = {
    "content_quality": 0.35,
    "reasoning": 0.40,
    "communication_clarity": 0.25,
}


def rubric_system_hint() -> str:
    return (
        "Rubric dimensions (0-100 each): "
        "content_quality = job-relevant substance and accuracy of claims; "
        "reasoning = logical structure, tradeoffs, problem decomposition; "
        "communication_clarity = concise, intelligible spoken-style answer (from transcript only). "
        f"Combine using weights: {RUBRIC_WEIGHTS}. "
        "Do not infer demographic attributes. Do not penalize or reward accent; judge only transcript text."
    )


def static_fallback_questions() -> list[dict[str, Any]]:
    """Used when GROQ_API_KEY is missing (offline dev)."""
    return [
        {
            "question_text": (
                "Describe a production incident you owned end-to-end. "
                "What was the user impact, how did you triage, and what mitigation did you ship?"
            ),
            "skill_target": "reliability_ownership",
            "difficulty": "mid",
        },
        {
            "question_text": (
                "How would you design an idempotent API for a payment capture flow? "
                "Mention failure modes and how clients should retry."
            ),
            "skill_target": "api_design",
            "difficulty": "mid",
        },
        {
            "question_text": (
                "Explain how you would optimize a slow PostgreSQL query when EXPLAIN shows a sequential scan."
            ),
            "skill_target": "databases",
            "difficulty": "senior",
        },
    ]
