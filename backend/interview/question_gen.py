from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

logger = logging.getLogger("fair-hiring.interview.question_gen")


class GeneratedQuestion(BaseModel):
    question_text: str = Field(..., min_length=20)
    skill_target: str = Field(default="general")
    difficulty: str = Field(default="mid", pattern="^(junior|mid|senior)$")


class GeneratedQuestionBatch(BaseModel):
    """LLM returns a list; we normalize to `count` items in generate_questions_batch."""

    questions: list[GeneratedQuestion] = Field(default_factory=list)


def _groq_api_key() -> str:
    """Normalize key from env (handles stray whitespace / wrapping quotes from .env files)."""
    raw = os.environ.get("GROQ_API_KEY") or ""
    if not raw:
        return ""
    s = str(raw).strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1].strip()
    return s


def _jd_excerpt(job_description: str, max_len: int = 280) -> str:
    one = " ".join(job_description.strip().split())
    if not one:
        return "this open role"
    return one[:max_len] + ("…" if len(one) > max_len else "")


def _skill_rotation(skills: list[str], count: int) -> list[str]:
    cleaned = [s.strip() for s in skills if isinstance(s, str) and s.strip()]
    if not cleaned:
        return ["a key requirement from the job description"] * max(1, count)
    return [cleaned[i % len(cleaned)] for i in range(count)]


# Distinct angles so a 5-question session does not feel like mock repeats.
_JD_QUESTION_TEMPLATES: list[tuple[str, str, str]] = [
    (
        "role_alignment",
        "junior",
        'The posting includes: "{excerpt}" In a spoken answer, which parts of this role match your background best, and what is one area where you would need to ramp up?',
    ),
    (
        "prioritized_delivery",
        "mid",
        'Given this summary of the job: "{excerpt}" If you joined next week, how would you prioritize your first two weeks to deliver value without over-scoping?',
    ),
    (
        "skill_depth",
        "mid",
        'The employer highlights work involving "{skill}". Using the context "{excerpt}" describe a concrete example where you applied "{skill}" end-to-end (problem, what you did, outcome).',
    ),
    (
        "tradeoffs",
        "senior",
        'From "{excerpt}" pick one technical tradeoff the team likely faces. Explain both sides and how you would decide in production.',
    ),
    (
        "reliability",
        "mid",
        'Considering "{excerpt}" how would you approach observability and incident response for the systems implied by this role?',
    ),
    (
        "collaboration",
        "mid",
        'Based on "{excerpt}" how do you communicate technical decisions to non-technical stakeholders when scope or deadlines shift?',
    ),
    (
        "security_privacy",
        "senior",
        'Reading "{excerpt}" what security or data-privacy risks would you watch for, and what mitigations would you bake into design?',
    ),
    (
        "testing_quality",
        "mid",
        'For responsibilities suggested by "{excerpt}" what is your testing strategy before shipping a risky change?',
    ),
    (
        "scalability",
        "senior",
        'Infer scale challenges from "{excerpt}" and explain how you would validate performance before scaling traffic or data volume.',
    ),
    (
        "debt_refactor",
        "mid",
        'If the codebase behind "{excerpt}" had legacy debt, how would you balance refactors versus shipping features?',
    ),
    (
        "mentoring",
        "mid",
        'Given "{excerpt}" how would you help a junior teammate grow while still meeting delivery expectations?',
    ),
    (
        "ambiguous_requirements",
        "junior",
        'When requirements in "{excerpt}" are ambiguous, what questions do you ask first and how do you document alignment?',
    ),
]


def jd_derived_questions(
    job_description: str,
    skills: list[str],
    count: int,
    *,
    start_index: int = 0,
) -> list[dict[str, Any]]:
    """
    Job-description-grounded questions when Groq is unavailable or as a last resort.
    Text is built from the actual JD excerpt + rotating skills — not a fixed mock bank.
    """
    if count < 1:
        return []
    excerpt = _jd_excerpt(job_description)
    skill_list = _skill_rotation(skills, count)
    out: list[dict[str, Any]] = []
    for i in range(count):
        idx = (start_index + i) % len(_JD_QUESTION_TEMPLATES)
        skill_target, difficulty, tmpl = _JD_QUESTION_TEMPLATES[idx]
        skill = skill_list[i]
        qtext = tmpl.format(excerpt=excerpt, skill=skill)
        out.append(
            {
                "question_text": qtext,
                "skill_target": skill_target,
                "difficulty": difficulty,
                "generated_json": {
                    "source": "jd_derived",
                    "template_index": idx,
                    "order_index": start_index + i + 1,
                },
            }
        )
    return out


def _llm() -> ChatGroq:
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    key = _groq_api_key()
    kwargs: dict[str, Any] = {"model": model, "temperature": 0.2}
    if key:
        kwargs["api_key"] = key
    return ChatGroq(**kwargs)


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
    key = _groq_api_key()
    if not key:
        row = jd_derived_questions(job_description, skills, 1, start_index=order_index - 1)[0]
        logger.info("No GROQ_API_KEY; using JD-derived interview question index %s", order_index)
        return row

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
        result: GeneratedQuestion = await llm.ainvoke([("system", system), ("human", human)])
    except Exception as exc:
        logger.warning("Groq question generation failed (%s); using JD-derived fallback.", exc)
        return jd_derived_questions(job_description, skills, 1, start_index=order_index - 1)[0]
    return {
        "question_text": result.question_text.strip(),
        "skill_target": result.skill_target.strip(),
        "difficulty": result.difficulty if result.difficulty in ("junior", "mid", "senior") else "mid",
        "generated_json": json.loads(result.model_dump_json()),
    }


async def _sequential_llm_questions(
    job_description: str,
    skills: list[str],
    count: int,
) -> list[dict[str, Any]]:
    """One LLM call per question — slower but robust when batch structured output fails."""
    out: list[dict[str, Any]] = []
    for i in range(count):
        prior = [{"question": x["question_text"], "answer": ""} for x in out[-3:]]
        one = await generate_question(
            job_description=job_description,
            skills=skills,
            order_index=i + 1,
            prior_qa=prior,
        )
        out.append(one)
    return out


async def generate_questions_batch(
    job_description: str,
    skills: list[str],
    count: int,
) -> list[dict[str, Any]]:
    """Return `count` question dicts for persisting as InterviewQuestion rows (order 1..count)."""
    if count < 1:
        return []
    key = _groq_api_key()
    if not key:
        logger.info("No GROQ_API_KEY; using JD-derived batch of %s questions", count)
        return jd_derived_questions(job_description, skills, count, start_index=0)

    skills_s = ", ".join(skills) if skills else "infer from job description"
    system = (
        "You generate a full technical interview as JSON. "
        f"Return exactly {count} distinct questions in the `questions` array. "
        "Each question must be job-relevant, fair, and free of discriminatory scenarios. "
        "Do not ask about age, family, health, religion, nationality, or protected traits. "
        "Vary difficulty across junior, mid, and senior; spread across different skill areas from the JD. "
        "Questions should be non-overlapping and suitable for spoken answers (no multi-page coding dumps). "
        "Ground every question in the provided job description (quote or paraphrase concrete duties/tools)."
    )
    human = (
        f"Job description:\n{job_description[:8000]}\n\n"
        f"Highlighted skills: {skills_s}\n\n"
        f"Produce exactly {count} questions in order (1 = warm-up, later = deeper)."
    )
    llm = _llm().with_structured_output(GeneratedQuestionBatch)
    try:
        batch: GeneratedQuestionBatch = await llm.ainvoke([("system", system), ("human", human)])
    except Exception as exc:
        logger.warning(
            "Groq batch question generation failed (%s); falling back to sequential JD-grounded calls.",
            exc,
        )
        return await _sequential_llm_questions(job_description, skills, count)

    raw = batch.questions
    if len(raw) == 0:
        logger.warning("Batch returned 0 questions; using sequential JD-grounded generation.")
        return await _sequential_llm_questions(job_description, skills, count)
    if len(raw) != count:
        logger.warning(
            "Batch returned %s questions, expected %s; padding with sequential singles.",
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
