from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InterviewStartRequest(BaseModel):
    job_description: str = Field(..., min_length=10)
    skills: list[str] = Field(default_factory=list)
    resume_score: float | None = Field(default=None, ge=0, le=100)
    test_score: float | None = Field(default=None, ge=0, le=100)


class QuestionDTO(BaseModel):
    id: str
    order_index: int
    question_text: str
    skill_target: str
    difficulty: str


class InterviewStartResponse(BaseModel):
    id: str
    status: str
    total_questions: int = 5
    first_question: QuestionDTO | None = None


class JoinResponse(BaseModel):
    id: str
    status: str
    joined_at: str | None = None


class NextQuestionResponse(BaseModel):
    interview_complete: bool
    question: QuestionDTO | None = None


class TranscriptSegmentDTO(BaseModel):
    id: str
    question_id: str | None
    t_start_ms: int
    t_end_ms: int
    text: str
    source: str


class TranscriptResponse(BaseModel):
    session_id: str
    segments: list[TranscriptSegmentDTO]


class EvaluationDTO(BaseModel):
    question_id: str
    rubric_id: str
    scores: dict[str, Any]
    explanation: str
    model_id: str


class AggregatedScores(BaseModel):
    resume: float | None
    test: float | None
    interview: float | None
    combined: float | None
    weights: dict[str, float]


class InterviewResultsResponse(BaseModel):
    session_id: str
    status: str
    evaluations: list[EvaluationDTO]
    interview_average: float | None
    aggregated: AggregatedScores
    hire_decision: str | None = None
    hire_rationale: str | None = None


class WebRTCOfferRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    sdp: str
    type: str = Field(default="offer", description="SDP type from client (typically 'offer').")


class WebRTCOfferResponse(BaseModel):
    sdp: str
    type: str = "answer"
