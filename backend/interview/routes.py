from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from interview import evaluation as evaluation_engine
from interview import hire as hire_mod
from interview import orchestrator as orch
from interview import question_gen
from interview import transcription as transcription_mod
from interview import webrtc_signaling as wrtc
from interview.aggregator import aggregate_scores
from interview.db import get_session_dep
from interview.models import (
    CandidateResponse,
    EvaluationResult,
    InterviewQuestion,
    InterviewSession,
    TranscriptSegment,
)
from interview.rubrics import RUBRIC_ID_SOFTWARE_ENGINEER
from interview.schemas import (
    AggregatedScores,
    EvaluationDTO,
    InterviewResultsResponse,
    InterviewStartRequest,
    InterviewStartResponse,
    JoinResponse,
    NextQuestionResponse,
    QuestionDTO,
    TranscriptResponse,
    TranscriptSegmentDTO,
    WebRTCOfferRequest,
    WebRTCOfferResponse,
)

logger = logging.getLogger("fair-hiring.interview.routes")

router = APIRouter(prefix="/interview", tags=["interview"])


async def _ensure_hire_decision(db: AsyncSession, s: InterviewSession) -> None:
    """Set hire_decision / hire_rationale once when interview is complete."""
    if s.hire_decision or s.status != "COMPLETED":
        return
    avg = await orch.interview_score_average(db, s.id)
    agg = aggregate_scores(s.resume_score, s.test_score, avg)
    combined = agg.get("combined")
    if isinstance(combined, (int, float)):
        combined_f: float | None = float(combined)
    else:
        combined_f = None
    decision, rationale = hire_mod.decide_hire(combined_f, avg, s.resume_score)
    s.hire_decision = decision
    s.hire_rationale = rationale
    await orch.log_audit(db, s.id, "hire_decided", {"decision": decision})


def _q_to_dto(q: InterviewQuestion) -> QuestionDTO:
    return QuestionDTO(
        id=q.id,
        order_index=q.order_index,
        question_text=q.question_text,
        skill_target=q.skill_target or "",
        difficulty=q.difficulty or "mid",
    )


@router.post("/start", response_model=InterviewStartResponse)
async def interview_start(
    body: InterviewStartRequest,
    db: AsyncSession = Depends(get_session_dep),
) -> InterviewStartResponse:
    sid = str(uuid.uuid4())
    skills = body.skills or []
    session = InterviewSession(
        id=sid,
        status="CREATED",
        job_description=body.job_description.strip(),
        skills_json=json.dumps(skills),
        resume_score=body.resume_score,
        test_score=body.test_score,
    )
    db.add(session)
    await orch.log_audit(db, sid, "session_created", {"skills": skills})
    nmax = orch.max_questions()
    batch = await question_gen.generate_questions_batch(
        job_description=body.job_description,
        skills=skills,
        count=nmax,
    )
    for i, qdata in enumerate(batch, start=1):
        qrow = InterviewQuestion(
            id=str(uuid.uuid4()),
            session_id=sid,
            order_index=i,
            question_text=qdata["question_text"],
            skill_target=qdata["skill_target"],
            difficulty=qdata["difficulty"],
            generated_json=qdata.get("generated_json"),
        )
        db.add(qrow)
    await db.commit()
    await db.refresh(session)
    questions = await orch.list_questions(db, sid)
    first = questions[0] if questions else None
    return InterviewStartResponse(
        id=sid,
        status=session.status,
        total_questions=len(questions),
        first_question=_q_to_dto(first) if first else None,
    )


@router.post("/{session_id}/join", response_model=JoinResponse)
async def interview_join(
    session_id: str,
    db: AsyncSession = Depends(get_session_dep),
) -> JoinResponse:
    s = await orch.load_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    now = datetime.now(timezone.utc)
    if s.joined_at is None:
        s.joined_at = now
        if s.status == "CREATED":
            s.status = "JOINED"
        await orch.log_audit(db, session_id, "candidate_joined", {})
    await db.commit()
    await db.refresh(s)
    return JoinResponse(
        id=s.id,
        status=s.status,
        joined_at=s.joined_at.isoformat() if s.joined_at else None,
    )


@router.post("/{session_id}/next-question", response_model=NextQuestionResponse)
async def interview_next_question(
    session_id: str,
    db: AsyncSession = Depends(get_session_dep),
) -> NextQuestionResponse:
    s = await orch.load_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if s.status == "COMPLETED":
        return NextQuestionResponse(interview_complete=True, question=None)

    open_q = await orch.current_open_question(db, session_id)
    if open_q:
        if s.status in ("CREATED", "JOINED"):
            s.status = "IN_PROGRESS"
            await db.commit()
        return NextQuestionResponse(interview_complete=False, question=_q_to_dto(open_q))

    answered = await orch.answered_question_ids(db, session_id)
    n_answered = len(answered)
    mx = orch.max_questions()
    if n_answered >= mx:
        s.status = "COMPLETED"
        s.completed_at = datetime.now(timezone.utc)
        await orch.log_audit(db, session_id, "interview_completed", {"reason": "max_questions"})
        await _ensure_hire_decision(db, s)
        await db.commit()
        await wrtc.close_peer(session_id)
        return NextQuestionResponse(interview_complete=True, question=None)

    questions = await orch.list_questions(db, session_id)
    order = len(questions) + 1
    prior = await orch.prior_qa_summary(db, session_id)
    skills = json.loads(s.skills_json or "[]")
    if not isinstance(skills, list):
        skills = []
    qdata = await question_gen.generate_question(
        job_description=s.job_description,
        skills=skills,
        order_index=order,
        prior_qa=prior,
    )
    qn = InterviewQuestion(
        id=str(uuid.uuid4()),
        session_id=session_id,
        order_index=order,
        question_text=qdata["question_text"],
        skill_target=qdata["skill_target"],
        difficulty=qdata["difficulty"],
        generated_json=qdata.get("generated_json"),
    )
    db.add(qn)
    s.status = "IN_PROGRESS"
    await orch.log_audit(db, session_id, "question_issued", {"order_index": order, "question_id": qn.id})
    await db.commit()
    await db.refresh(qn)
    return NextQuestionResponse(interview_complete=False, question=_q_to_dto(qn))


@router.post("/{session_id}/submit-audio")
async def interview_submit_audio(
    session_id: str,
    question_id: str = Form(...),
    audio: UploadFile | None = File(None),
    transcript: str | None = Form(None),
    db: AsyncSession = Depends(get_session_dep),
) -> dict:
    s = await orch.load_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if s.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Interview already completed.")

    q_stmt = select(InterviewQuestion).where(
        InterviewQuestion.id == question_id,
        InterviewQuestion.session_id == session_id,
    )
    question = (await db.execute(q_stmt)).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found for this session.")

    existing = await db.execute(
        select(CandidateResponse.id).where(
            CandidateResponse.question_id == question_id,
            CandidateResponse.session_id == session_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="This question was already answered.")

    text: str
    source = "upload"
    audio_ref: str | None = None
    if transcript is not None and transcript.strip():
        text = transcript.strip()
        source = "override"
    elif audio is not None:
        raw = await audio.read()
        audio_ref = audio.filename or "upload.bin"
        transcriber = transcription_mod.get_transcriber()
        text = await transcriber.transcribe(
            raw, filename=audio_ref, mime=audio.content_type or "application/octet-stream"
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either `transcript` text or `audio` file.",
        )

    seg = TranscriptSegment(
        id=str(uuid.uuid4()),
        session_id=session_id,
        question_id=question_id,
        t_start_ms=0,
        t_end_ms=0,
        text=text,
        source=source,
    )
    db.add(seg)
    resp_row = CandidateResponse(
        id=str(uuid.uuid4()),
        session_id=session_id,
        question_id=question_id,
        transcript_text=text,
        audio_ref=audio_ref,
    )
    db.add(resp_row)

    ev = await evaluation_engine.evaluate_answer(
        job_description=s.job_description,
        question_text=question.question_text,
        transcript=text,
        rubric_id=RUBRIC_ID_SOFTWARE_ENGINEER,
    )
    eval_row = EvaluationResult(
        id=str(uuid.uuid4()),
        session_id=session_id,
        question_id=question_id,
        rubric_id=RUBRIC_ID_SOFTWARE_ENGINEER,
        scores_json=ev["scores_json"],
        explanation=ev["explanation"],
        model_id=ev["model_id"],
    )
    db.add(eval_row)
    await orch.log_audit(
        db,
        session_id,
        "response_evaluated",
        {"question_id": question_id, "model_id": ev["model_id"]},
    )

    await db.flush()
    n_done = await db.scalar(
        select(func.count()).select_from(CandidateResponse).where(
            CandidateResponse.session_id == session_id
        )
    )
    n_done = int(n_done or 0)
    if n_done >= orch.max_questions():
        s.status = "COMPLETED"
        s.completed_at = datetime.now(timezone.utc)
        await orch.log_audit(db, session_id, "interview_completed", {"reason": "answered_max"})
        await wrtc.close_peer(session_id)

    if s.status == "COMPLETED":
        await _ensure_hire_decision(db, s)

    await db.commit()
    return {
        "ok": True,
        "session_id": session_id,
        "question_id": question_id,
        "evaluation_id": eval_row.id,
        "scores": ev["scores_json"],
        "interview_complete": s.status == "COMPLETED",
    }


@router.get("/{session_id}/transcript", response_model=TranscriptResponse)
async def interview_get_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_session_dep),
) -> TranscriptResponse:
    s = await orch.load_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.t_start_ms, TranscriptSegment.id)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    return TranscriptResponse(
        session_id=session_id,
        segments=[
            TranscriptSegmentDTO(
                id=r.id,
                question_id=r.question_id,
                t_start_ms=r.t_start_ms,
                t_end_ms=r.t_end_ms,
                text=r.text,
                source=r.source,
            )
            for r in rows
        ],
    )


@router.get("/{session_id}/results", response_model=InterviewResultsResponse)
async def interview_get_results(
    session_id: str,
    db: AsyncSession = Depends(get_session_dep),
) -> InterviewResultsResponse:
    s = await orch.load_session(db, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if s.status == "COMPLETED" and not s.hire_decision:
        await _ensure_hire_decision(db, s)
        await db.commit()
        await db.refresh(s)
    stmt = select(EvaluationResult).where(EvaluationResult.session_id == session_id)
    evs = list((await db.execute(stmt)).scalars().all())
    avg = await orch.interview_score_average(db, session_id)
    agg = aggregate_scores(s.resume_score, s.test_score, avg)
    evaluations = [
        EvaluationDTO(
            question_id=e.question_id,
            rubric_id=e.rubric_id,
            scores=e.scores_json,
            explanation=e.explanation,
            model_id=e.model_id,
        )
        for e in evs
    ]
    return InterviewResultsResponse(
        session_id=session_id,
        status=s.status,
        evaluations=evaluations,
        interview_average=avg,
        aggregated=AggregatedScores(
            resume=agg["resume"],
            test=agg["test"],
            interview=agg["interview"],
            combined=agg["combined"],
            weights=agg["weights"],
        ),
        hire_decision=s.hire_decision,
        hire_rationale=s.hire_rationale,
    )


@router.post("/{session_id}/webrtc/offer", response_model=WebRTCOfferResponse)
async def interview_webrtc_offer(
    session_id: str,
    body: WebRTCOfferRequest,
    db: AsyncSession = Depends(get_session_dep),
) -> WebRTCOfferResponse:
    """WebRTC is not available in the serverless deployment."""
    raise HTTPException(
        status_code=501,
        detail=(
            "WebRTC peer connections are not supported in the serverless deployment. "
            "Use the audio-upload submission flow instead."
        ),
    )
