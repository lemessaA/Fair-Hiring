"""LangGraph workflow for analyzing and ranking a single anonymized resume.

The graph runs two Groq calls per candidate:
  1. analyze  -> extract structured skills / experience from masked resume
  2. score    -> grade fit against the job description, returning matched
                 skills, missing skills, strengths and gaps.

Each node uses ``with_structured_output`` so the model returns typed JSON
that we can render directly in the UI.
"""

from __future__ import annotations

import os
from typing import TypedDict

from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field


GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


class CandidateAnalysis(BaseModel):
    """Structured extraction from an anonymized resume."""

    skills: list[str] = Field(
        default_factory=list,
        description="Concrete technical and professional skills present in the resume.",
    )
    years_experience: float = Field(
        0.0,
        description="Best estimate of total years of relevant professional experience.",
    )
    education_level: str = Field(
        "Unknown",
        description="Highest education level (e.g. 'Bachelor', 'Master', 'PhD', 'Bootcamp', 'Unknown').",
    )
    summary: str = Field(
        "",
        description="One- or two-sentence neutral summary of the candidate's background.",
    )


class CandidateScore(BaseModel):
    """Skill-based fit score against a job description."""

    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Overall fit, 0-100, based ONLY on skills, experience and qualifications.",
    )
    matched_skills: list[str] = Field(
        default_factory=list,
        description="Skills required by the job that the candidate clearly demonstrates.",
    )
    missing_skills: list[str] = Field(
        default_factory=list,
        description="Skills required by the job that the candidate appears to lack.",
    )
    strengths: str = Field(
        "",
        description="One- or two-sentence neutral description of the candidate's strongest fit signals.",
    )
    gaps: str = Field(
        "",
        description="One- or two-sentence neutral description of the candidate's biggest gaps.",
    )


class RankState(TypedDict, total=False):
    job_description: str
    masked_resume: str
    analysis: dict
    score: dict


def _llm() -> ChatGroq:
    return ChatGroq(model=GROQ_MODEL, temperature=0.0)


def _analyze_node(state: RankState) -> RankState:
    llm = _llm().with_structured_output(CandidateAnalysis)
    system = (
        "You are a fair-hiring assistant. The resume below has had personal "
        "information (email, phone, address, gendered terms) redacted. "
        "Extract the candidate's skills and qualifications neutrally, "
        "ignoring any remaining identity signals. Never speculate about "
        "gender, ethnicity, or age."
    )
    result: CandidateAnalysis = llm.invoke(
        [
            ("system", system),
            ("human", f"Anonymized resume:\n\n{state['masked_resume']}"),
        ]
    )
    return {"analysis": result.model_dump()}


def _score_node(state: RankState) -> RankState:
    llm = _llm().with_structured_output(CandidateScore)
    analysis = state.get("analysis", {})
    system = (
        "You are a fair-hiring assistant scoring candidates strictly on "
        "skills, experience and qualifications. Do NOT consider names, "
        "schools' prestige, locations, or any demographic signal. "
        "Score the candidate 0-100 based on how well their skills match "
        "the job description. Be specific and consistent."
    )
    human = (
        f"Job description:\n{state['job_description']}\n\n"
        f"Anonymized resume:\n{state['masked_resume']}\n\n"
        f"Extracted analysis: {analysis}"
    )
    result: CandidateScore = llm.invoke(
        [("system", system), ("human", human)]
    )
    return {"score": result.model_dump()}


def build_graph():
    graph = StateGraph(RankState)
    graph.add_node("analyze", _analyze_node)
    graph.add_node("score", _score_node)
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "score")
    graph.add_edge("score", END)
    return graph.compile()


# Compile once at import time so each request reuses the same graph object.
ranking_graph = build_graph()
