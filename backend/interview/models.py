from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class InterviewSession(Base):
    __tablename__ = "interview_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(32), default="CREATED")
    job_description: Mapped[str] = mapped_column(Text)
    skills_json: Mapped[str] = mapped_column(Text, default="[]")
    resume_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    test_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    webrtc_meta_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hire_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    hire_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    questions: Mapped[list["InterviewQuestion"]] = relationship(back_populates="session")
    segments: Mapped[list["TranscriptSegment"]] = relationship(back_populates="session")
    responses: Mapped[list["CandidateResponse"]] = relationship(back_populates="session")
    evaluations: Mapped[list["EvaluationResult"]] = relationship(back_populates="session")
    audit_logs: Mapped[list["InterviewAuditLog"]] = relationship(back_populates="session")


class InterviewQuestion(Base):
    __tablename__ = "interview_question"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_session.id", ondelete="CASCADE"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    question_text: Mapped[str] = mapped_column(Text)
    skill_target: Mapped[str] = mapped_column(String(512), default="")
    difficulty: Mapped[str] = mapped_column(String(32), default="mid")
    generated_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["InterviewSession"] = relationship(back_populates="questions")
    responses: Mapped[list["CandidateResponse"]] = relationship(back_populates="question")
    evaluations: Mapped[list["EvaluationResult"]] = relationship(back_populates="question")
    segments: Mapped[list["TranscriptSegment"]] = relationship(back_populates="question")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segment"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_session.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("interview_question.id", ondelete="SET NULL"), nullable=True
    )
    t_start_ms: Mapped[int] = mapped_column(Integer, default=0)
    t_end_ms: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="upload")  # upload | webrtc_chunk | override

    session: Mapped["InterviewSession"] = relationship(back_populates="segments")
    question: Mapped["InterviewQuestion | None"] = relationship(back_populates="segments")


class CandidateResponse(Base):
    __tablename__ = "candidate_response"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_session.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_question.id", ondelete="CASCADE"), index=True
    )
    transcript_text: Mapped[str] = mapped_column(Text)
    audio_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    session: Mapped["InterviewSession"] = relationship(back_populates="responses")
    question: Mapped["InterviewQuestion"] = relationship(back_populates="responses")


class EvaluationResult(Base):
    __tablename__ = "evaluation_result"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_session.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_question.id", ondelete="CASCADE"), index=True
    )
    rubric_id: Mapped[str] = mapped_column(String(64), default="software_engineer_v1")
    scores_json: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text, default="")
    model_id: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="evaluations")
    question: Mapped["InterviewQuestion"] = relationship(back_populates="evaluations")


class InterviewAuditLog(Base):
    __tablename__ = "interview_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_session.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="audit_logs")
