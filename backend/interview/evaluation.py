from __future__ import annotations

import logging
import os
from typing import Any, Literal

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from interview.rubrics import RUBRIC_ID_SOFTWARE_ENGINEER, RUBRIC_WEIGHTS, rubric_system_hint

logger = logging.getLogger("fair-hiring.interview.evaluation")


class RubricEvaluation(BaseModel):
    content_quality: int = Field(ge=0, le=100)
    reasoning: int = Field(ge=0, le=100)
    communication_clarity: int = Field(ge=0, le=100)
    explanation: str = Field(
        ...,
        description="Short evidence-based rationale referencing transcript wording only.",
    )
    text_sentiment: str = Field(
        default="neutral",
        pattern="^(positive|neutral|negative)$",
        description="Tone of answer text only (not facial).",
    )


def _llm() -> ChatGroq:
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(model=model, temperature=0.0)


def _weighted(cq: int, r: int, cc: int) -> int:
    w = RUBRIC_WEIGHTS
    total = (
        cq * w["content_quality"]
        + r * w["reasoning"]
        + cc * w["communication_clarity"]
    )
    return int(round(total))


async def evaluate_answer(
    *,
    job_description: str,
    question_text: str,
    transcript: str,
    rubric_id: str = RUBRIC_ID_SOFTWARE_ENGINEER,
) -> dict[str, Any]:
    """Evaluate transcript only (no audio/video). Returns scores_json-shaped dict + explanation + model."""
    key = os.environ.get("GROQ_API_KEY", "")
    if not key or not transcript.strip():
        # Offline heuristic
        base = min(85, 40 + min(len(transcript) // 25, 45))
        cq, rsn, clr = base, max(0, base - 5), min(100, base + 5)
        wt = _weighted(cq, rsn, clr)
        scores_json = {
            "content_quality": cq,
            "reasoning": rsn,
            "communication_clarity": clr,
            "weighted_total": wt,
            "text_sentiment": "neutral",
        }
        return {
            "scores_json": scores_json,
            "explanation": (
                "Offline heuristic scoring (no GROQ_API_KEY or empty transcript): "
                "length-based placeholder only — configure Groq for real rubric evaluation."
            ),
            "model_id": "heuristic_v0",
        }

    system = (
        "You are a fair hiring evaluator. Input is ONLY the candidate's spoken answer as a text transcript. "
        "You must NOT infer gender, race, age, attractiveness, accent origin, or any protected characteristic. "
        "Do not reward or penalize speaking style associated with any demographic. "
        "Score strictly on job-relevant content, reasoning quality, and clarity of the answer. "
        + rubric_system_hint()
        + " Return structured JSON matching the schema. "
        "text_sentiment must reflect overall tone of the answer text only (positive|neutral|negative)."
    )
    human = (
        f"Job description (context):\n{job_description[:4000]}\n\n"
        f"Interview question:\n{question_text}\n\n"
        f"Candidate transcript:\n{transcript[:8000]}\n"
    )
    llm = _llm().with_structured_output(RubricEvaluation)
    try:
        result: RubricEvaluation = await llm.ainvoke([("system", system), ("human", human)])
    except Exception as exc:
        logger.warning("Groq evaluation failed (%s); using heuristic fallback.", exc)
        base = min(85, 40 + min(len(transcript) // 25, 45))
        cq, rsn, clr = base, max(0, base - 5), min(100, base + 5)
        wt = _weighted(cq, rsn, clr)
        return {
            "scores_json": {
                "content_quality": cq,
                "reasoning": rsn,
                "communication_clarity": clr,
                "weighted_total": wt,
                "text_sentiment": "neutral",
            },
            "explanation": f"Heuristic fallback after model error: {str(exc)[:300]}",
            "model_id": "heuristic_fallback",
        }
    wt = _weighted(result.content_quality, result.reasoning, result.communication_clarity)
    scores_json = {
        "content_quality": result.content_quality,
        "reasoning": result.reasoning,
        "communication_clarity": result.communication_clarity,
        "weighted_total": wt,
        "text_sentiment": result.text_sentiment,
    }
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    return {
        "scores_json": scores_json,
        "explanation": result.explanation.strip(),
        "model_id": model,
    }
