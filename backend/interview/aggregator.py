from __future__ import annotations

import os
from typing import Any


def _f(name: str, default: float) -> float:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return float(v)


def aggregate_scores(
    resume: float | None,
    test: float | None,
    interview: float | None,
) -> dict[str, Any]:
    """Weighted combined score; missing components renormalized over available weights."""
    wr = _f("AGGREGATOR_WEIGHT_RESUME", 0.4)
    wt = _f("AGGREGATOR_WEIGHT_TEST", 0.3)
    wi = _f("AGGREGATOR_WEIGHT_INTERVIEW", 0.3)

    parts: list[tuple[float, float]] = []
    if resume is not None:
        parts.append((wr, resume))
    if test is not None:
        parts.append((wt, test))
    if interview is not None:
        parts.append((wi, interview))

    if not parts:
        return {
            "resume": resume,
            "test": test,
            "interview": interview,
            "combined": None,
            "weights": {"resume": wr, "test": wt, "interview": wi},
        }

    wsum = sum(p[0] for p in parts)
    combined = sum(w * s for w, s in parts) / wsum if wsum else None
    return {
        "resume": resume,
        "test": test,
        "interview": interview,
        "combined": round(float(combined), 2) if combined is not None else None,
        "weights": {"resume": wr, "test": wt, "interview": wi},
    }
