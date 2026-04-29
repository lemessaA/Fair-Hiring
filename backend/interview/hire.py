from __future__ import annotations

import logging
import os

logger = logging.getLogger("fair-hiring.interview.hire")


def decide_hire(
    combined: float | None,
    interview_average: float | None,
    resume_score: float | None,
) -> tuple[str, str]:
    """
    Rule-based hiring recommendation from aggregate signals.
    Returns (decision, rationale) where decision is APPROVED or REJECTED.
    """
    threshold = float(os.environ.get("HIRE_COMBINED_THRESHOLD", "62"))
    interview_floor = float(os.environ.get("HIRE_INTERVIEW_FLOOR", "45"))

    if combined is not None:
        if combined >= threshold:
            return (
                "APPROVED",
                f"Combined score {combined:.1f} meets the hiring threshold ({threshold}).",
            )
        return (
            "REJECTED",
            f"Combined score {combined:.1f} is below the hiring threshold ({threshold}).",
        )

    # No combined (missing components): fall back to interview-only if present
    if interview_average is not None:
        if interview_average >= interview_floor:
            return (
                "APPROVED",
                f"Interview average {interview_average:.1f} meets the interview-only floor ({interview_floor}).",
            )
        return (
            "REJECTED",
            f"Interview average {interview_average:.1f} is below the interview-only floor ({interview_floor}).",
        )

    if resume_score is not None:
        if resume_score >= threshold:
            return (
                "APPROVED",
                f"Resume score {resume_score:.1f} meets the threshold ({threshold}); interview data was unavailable.",
            )
        return (
            "REJECTED",
            f"Resume score {resume_score:.1f} is below the threshold ({threshold}); interview data was unavailable.",
        )

    logger.warning("Hire decision: no scores available; defaulting to REJECTED")
    return ("REJECTED", "Insufficient scoring data to support approval.")
