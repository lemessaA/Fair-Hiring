from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from interview.models import (
    CandidateResponse,
    EvaluationResult,
    InterviewAuditLog,
    InterviewQuestion,
    InterviewSession,
)

logger = logging.getLogger("fair-hiring.interview.orchestrator")


def max_questions() -> int:
    return int(os.environ.get("INTERVIEW_MAX_QUESTIONS", "5"))


async def log_audit(
    db: AsyncSession,
    session_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    row = InterviewAuditLog(
        id=str(uuid.uuid4()),
        session_id=session_id,
        event_type=event_type,
        payload_json=json.dumps(payload, default=str),
    )
    db.add(row)


async def load_session(db: AsyncSession, session_id: str) -> InterviewSession | None:
    stmt = select(InterviewSession).where(InterviewSession.id == session_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_questions(db: AsyncSession, session_id: str) -> list[InterviewQuestion]:
    stmt = (
        select(InterviewQuestion)
        .where(InterviewQuestion.session_id == session_id)
        .order_by(InterviewQuestion.order_index)
    )
    return list((await db.execute(stmt)).scalars().all())


async def answered_question_ids(db: AsyncSession, session_id: str) -> set[str]:
    stmt = select(CandidateResponse.question_id).where(CandidateResponse.session_id == session_id)
    rows = (await db.execute(stmt)).scalars().all()
    return set(rows)


async def current_open_question(
    db: AsyncSession, session_id: str
) -> InterviewQuestion | None:
    questions = await list_questions(db, session_id)
    answered = await answered_question_ids(db, session_id)
    for q in questions:
        if q.id not in answered:
            return q
    return None


async def prior_qa_summary(db: AsyncSession, session_id: str) -> list[dict[str, Any]]:
    stmt = (
        select(CandidateResponse, InterviewQuestion)
        .join(InterviewQuestion, CandidateResponse.question_id == InterviewQuestion.id)
        .where(CandidateResponse.session_id == session_id)
        .order_by(InterviewQuestion.order_index)
    )
    rows = (await db.execute(stmt)).all()
    out: list[dict[str, Any]] = []
    for resp, q in rows:
        out.append({"question": q.question_text, "answer": resp.transcript_text})
    return out


def score_total_from_eval_json(scores_json: dict[str, Any] | None) -> int:
    """Map one evaluation row to a 0–100 style total (matches prior interview average logic)."""
    scores = scores_json or {}
    wt = scores.get("weighted_total")
    if isinstance(wt, (int, float)):
        return int(wt)
    cq = int(scores.get("content_quality", 0))
    r = int(scores.get("reasoning", 0))
    cc = int(scores.get("communication_clarity", 0))
    return int(round((cq + r + cc) / 3))


async def interview_score_average(db: AsyncSession, session_id: str) -> float | None:
    stmt = select(EvaluationResult).where(EvaluationResult.session_id == session_id)
    evs = list((await db.execute(stmt)).scalars().all())
    if not evs:
        return None
    totals = [score_total_from_eval_json(e.scores_json) for e in evs]
    return round(sum(totals) / len(totals), 2)


async def interview_live_and_typed_averages(
    db: AsyncSession, session_id: str
) -> tuple[float | None, float | None]:
    """
    Split interview score by submission mode (same rubric, different inputs):
    - **Live** (80% target weight): answers submitted with an **audio** file (`audio_ref` set).
    - **Typed** (10% target weight): answers submitted as **transcript text only** (no `audio_ref`).
    """
    stmt = (
        select(EvaluationResult.scores_json, CandidateResponse.audio_ref)
        .join(
            CandidateResponse,
            and_(
                CandidateResponse.session_id == EvaluationResult.session_id,
                CandidateResponse.question_id == EvaluationResult.question_id,
            ),
        )
        .where(EvaluationResult.session_id == session_id)
    )
    rows = list((await db.execute(stmt)).all())
    live_totals: list[int] = []
    typed_totals: list[int] = []
    for scores_json, audio_ref in rows:
        v = score_total_from_eval_json(scores_json)
        if audio_ref:
            live_totals.append(v)
        else:
            typed_totals.append(v)
    live_avg = round(sum(live_totals) / len(live_totals), 2) if live_totals else None
    typed_avg = round(sum(typed_totals) / len(typed_totals), 2) if typed_totals else None
    return live_avg, typed_avg
