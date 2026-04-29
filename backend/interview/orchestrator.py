from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

from sqlalchemy import select
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


async def interview_score_average(db: AsyncSession, session_id: str) -> float | None:
    stmt = select(EvaluationResult).where(EvaluationResult.session_id == session_id)
    evs = list((await db.execute(stmt)).scalars().all())
    if not evs:
        return None
    totals: list[int] = []
    for e in evs:
        scores = e.scores_json or {}
        wt = scores.get("weighted_total")
        if isinstance(wt, (int, float)):
            totals.append(int(wt))
        else:
            cq = int(scores.get("content_quality", 0))
            r = int(scores.get("reasoning", 0))
            cc = int(scores.get("communication_clarity", 0))
            totals.append(int(round((cq + r + cc) / 3)))
    return round(sum(totals) / len(totals), 2)
