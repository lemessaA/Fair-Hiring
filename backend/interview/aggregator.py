from __future__ import annotations

from typing import Any


def aggregate_hire_scores(
    resume: float | None,
    live_interview: float | None,
    typed_interview: float | None,
    *,
    test_score: float | None = None,
    overall_interview: float | None = None,
) -> dict[str, Any]:
    """
    Hire **combined** score (0–100 scale inputs):

    - **80%** live / camera path: average evaluation score for answers submitted **with audio**
      (`audio_ref` set on the response).
    - **10%** typed path: average for **transcript-only** answers (no audio upload).
    - **10%** resume score from session input.

    If only one interview mode exists, its nominal weight absorbs the other interview slot
    (0.9 on that mode + 0.1 resume when both interview and resume exist; interview-only uses 1.0 on interview).
    ``test_score`` is returned for display only and is **not** part of the hire blend.
    """
    has_l = live_interview is not None
    has_t = typed_interview is not None
    has_r = resume is not None

    w_live = 0.8 if has_l else 0.0
    w_typed = 0.1 if has_t else 0.0
    w_resume = 0.1 if has_r else 0.0

    if has_t and not has_l:
        w_typed = 0.9
    elif has_l and not has_t:
        w_live = 0.9

    parts: list[tuple[float, float]] = []
    if w_live > 0 and has_l:
        parts.append((w_live, live_interview))
    if w_typed > 0 and has_t:
        parts.append((w_typed, typed_interview))
    if w_resume > 0 and has_r:
        parts.append((w_resume, resume))

    combined: float | None = None
    if parts:
        wsum = sum(w for w, _ in parts)
        if wsum > 0:
            combined = round(sum(w * s for w, s in parts) / wsum, 2)

    return {
        "resume": resume,
        "test": test_score,
        "interview": overall_interview,
        "interview_live": live_interview,
        "interview_typed": typed_interview,
        "combined": combined,
        "weights": {
            "hire_live": 0.8,
            "hire_typed": 0.1,
            "hire_resume": 0.1,
        },
    }
