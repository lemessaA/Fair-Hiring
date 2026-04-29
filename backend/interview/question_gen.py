from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from interview.rubrics import static_fallback_questions

logger = logging.getLogger("fair-hiring.interview.question_gen")


class GeneratedQuestion(BaseModel):
    question_text: str = Field(..., min_length=20)
    skill_target: str = Field(default="general")
    difficulty: str = Field(default="mid", pattern="^(junior|mid|senior)$")


class GeneratedQuestionBatch(BaseModel):
    """LLM returns a list; we normalize to `count` items in generate_questions_batch."""

    questions: list[GeneratedQuestion] = Field(default_factory=list)


def _llm() -> ChatGroq:
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(model=model, temperature=0.2)


def _prior_summary(prior_qa: list[dict[str, Any]]) -> str:
    if not prior_qa:
        return "(no prior answers yet)"
    parts = []
    for item in prior_qa[-3:]:
        parts.append(
            f"Q: {item.get('question','')[:200]}\nA transcript: {item.get('answer','')[:500]}"
        )
    return "\n---\n".join(parts)


async def generate_question(
    job_description: str,
    skills: list[str],
    order_index: int,
    prior_qa: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return dict suitable for InterviewQuestion row (question_text, skill_target, difficulty, generated_json)."""
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        pool = static_fallback_questions()
        pick = pool[(order_index - 1) % len(pool)]
        logger.info("No GROQ_API_KEY; using static interview question index %s", order_index)
        return {
            "question_text": pick["question_text"],
            "skill_target": pick["skill_target"],
            "difficulty": pick.get("difficulty", "mid"),
            "generated_json": {"source": "static_fallback", "order_index": order_index},
        }

    skills_s = ", ".join(skills) if skills else "infer from job description"
    system = (
        "You generate one fair technical interview question as JSON. "
        "The question must be job-relevant, free of discriminatory scenarios, and culturally neutral. "
        "Do not ask about age, family, health, religion, nationality, or protected traits. "
        "Tie the question to a concrete skill area. Difficulty must be junior, mid, or senior."
    )
    human = (
        f"Job description:\n{job_description[:6000]}\n\n"
        f"Highlighted skills: {skills_s}\n\n"
        f"Question sequence number: {order_index}\n"
        f"Prior Q/A summary:\n{_prior_summary(prior_qa)}\n\n"
        "Produce the next question that deepens assessment based on prior answers when present."
    )
    llm = _llm().with_structured_output(GeneratedQuestion)
    try:
        result: GeneratedQuestion = await llm.ainvoke(
            [("system", system), ("human", human)]
        )
    except Exception as exc:
        logger.warning("Groq question generation failed (%s); using static fallback.", exc)
        pool = static_fallback_questions()
        pick = pool[(order_index - 1) % len(pool)]
        return {
            "question_text": pick["question_text"],
            "skill_target": pick["skill_target"],
            "difficulty": pick.get("difficulty", "mid"),
            "generated_json": {
                "source": "llm_error_fallback",
                "error": str(exc)[:500],
                "order_index": order_index,
            },
        }
    return {
        "question_text": result.question_text.strip(),
        "skill_target": result.skill_target.strip(),
        "difficulty": result.difficulty if result.difficulty in ("junior", "mid", "senior") else "mid",
        "generated_json": json.loads(result.model_dump_json()),
    }


def _static_batch(count: int) -> list[dict[str, Any]]:
    pool = static_fallback_questions()
    out: list[dict[str, Any]] = []
    for i in range(count):
        pick = pool[i % len(pool)]
        out.append(
            {
                "question_text": f"[Session Q{i + 1}] {pick['question_text']}",
                "skill_target": pick["skill_target"],
                "difficulty": pick.get("difficulty", "mid"),
                "generated_json": {"source": "static_fallback", "order_index": i + 1},
            }
        )
    return out


async def generate_questions_batch(
    job_description: str,
    skills: list[str],
    count: int,
) -> list[dict[str, Any]]:
    """Return `count` question dicts for persisting as InterviewQuestion rows (order 1..count)."""
    if count < 1:
        return []
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        logger.info("No GROQ_API_KEY; using static batch of %s questions", count)
        return _static_batch(count)

    skills_s = ", ".join(skills) if skills else "infer from job description"
    system = (
        "You generate a full technical interview as JSON. "
        f"Return exactly {count} distinct questions in the `questions` array. "
        "Each question must be job-relevant, fair, and free of discriminatory scenarios. "
        "Do not ask about age, family, health, religion, nationality, or protected traits. "
        "Vary difficulty across junior, mid, and senior; spread across different skill areas from the JD. "
        "Questions should be non-overlapping and suitable for spoken answers (no multi-page coding dumps)."
    )
    human = (
        f"Job description:\n{job_description[:8000]}\n\n"
        f"Highlighted skills: {skills_s}\n\n"
        f"Produce exactly {count} questions in order (1 = warm-up, later = deeper)."
    )
    llm = _llm().with_structured_output(GeneratedQuestionBatch)
    try:
        batch: GeneratedQuestionBatch = await llm.ainvoke(
            [("system", system), ("human", human)]
        )
    except Exception as exc:
        logger.warning("Groq batch question generation failed (%s); using static fallback.", exc)
        return _static_batch(count)

    raw = batch.questions
    if len(raw) == 0:
        logger.warning("Batch returned 0 questions; using static fallback.")
        return _static_batch(count)
    if len(raw) != count:
        logger.warning(
            "Batch returned %s questions, expected %s; padding with singles.",
            len(raw),
            count,
        )
    out: list[dict[str, Any]] = []
    for i in range(count):
        if i < len(raw):
            g = raw[i]
            out.append(
                {
                    "question_text": g.question_text.strip(),
                    "skill_target": g.skill_target.strip(),
                    "difficulty": g.difficulty if g.difficulty in ("junior", "mid", "senior") else "mid",
                    "generated_json": json.loads(g.model_dump_json()),
                }
            )
            continue
        prior = [{"question": x["question_text"], "answer": ""} for x in out[-3:]]
        one = await generate_question(
            job_description=job_description,
            skills=skills,
            order_index=i + 1,
            prior_qa=prior,
        )
        out.append(one)
    return out
