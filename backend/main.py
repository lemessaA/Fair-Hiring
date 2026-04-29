"""FastAPI entrypoint for the Fair Hiring Network backend.

Routes are registered without the ``/api`` prefix because Vercel's
``experimentalServices`` strips ``routePrefix`` before forwarding the
request to this service.
"""

from __future__ import annotations

import io
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import fastapi
import fastapi.middleware.cors
from dotenv import load_dotenv
from fastapi import File, Form, UploadFile
from pypdf import PdfReader

# Load secrets (e.g. GROQ_API_KEY) from a local .env file when present.
load_dotenv(Path(__file__).resolve().parent / ".env")

from graph import ranking_graph
from interview.routes import router as interview_router
from interview.db import dispose_db, init_db
from interview.redis_client import shutdown_cache
from pii import mask_pii


logger = logging.getLogger("fair-hiring")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    await init_db()
    yield
    await shutdown_cache()
    await dispose_db()


app = fastapi.FastAPI(title="Fair Hiring Network API", lifespan=lifespan)

app.include_router(interview_router)

# Browser CORS only matters for direct calls to this API (not for Vercel rewrites,
# which are server-to-server). Comma-separated origins; unset => "*". Do not use
# allow_credentials=True with wildcard origins (invalid in browsers).
_cors_raw = (os.environ.get("CORS_ALLOW_ORIGINS") or "").strip()
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else ["*"]
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    interview_db_ok = False
    redis_ok = False
    try:
        from sqlalchemy import text

        from interview.db import get_engine

        eng = get_engine()
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
        interview_db_ok = True
    except Exception:
        interview_db_ok = False
    try:
        from interview.redis_client import get_cache

        c = get_cache()
        await c.set("__health__", "1", ttl_seconds=5)
        redis_ok = await c.get("__health__") == "1"
        await c.delete("__health__")
    except Exception:
        redis_ok = False
    return {
        "status": "ok",
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "groq_key_configured": bool(os.environ.get("GROQ_API_KEY")),
        "interview_db_ok": interview_db_ok,
        "redis_ok": redis_ok,
    }


def _extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to extract a PDF page: %s", exc)
    return "\n".join(pages).strip()


@app.post("/extract-jd")
async def extract_job_description(file: UploadFile = File(...)) -> dict[str, Any]:
    """Parse a job-description PDF and return its plain text.

    The frontend uses this to let recruiters drop a JD PDF in instead of
    pasting raw text. Returned text is editable before being sent to /rank.
    """
    filename = file.filename or "job-description.pdf"
    if not (file.content_type == "application/pdf" or filename.lower().endswith(".pdf")):
        raise fastapi.HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        raw = await file.read()
        text = _extract_pdf_text(raw)
    except Exception as exc:
        logger.exception("Failed to parse JD %s", filename)
        raise fastapi.HTTPException(status_code=400, detail=f"Could not read PDF: {exc}") from exc

    if not text:
        raise fastapi.HTTPException(
            status_code=422,
            detail="No extractable text found in this PDF. It may be a scanned image.",
        )

    return {
        "filename": filename,
        "word_count": len(text.split()),
        "text": text,
    }


@app.post("/rank")
async def rank_resumes(
    job_description: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    """Rank uploaded PDF resumes against a job description.

    Each resume is:
      1. Parsed (PDF -> text)
      2. PII-masked locally with regex (email, phone, address, gendered terms)
      3. Sent to a LangGraph workflow that calls Groq to analyze + score it
    """
    if not os.environ.get("GROQ_API_KEY"):
        raise fastapi.HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured on the server.",
        )

    if not files:
        raise fastapi.HTTPException(status_code=400, detail="No resumes uploaded.")

    if not job_description.strip():
        raise fastapi.HTTPException(status_code=400, detail="Job description is required.")

    candidates: list[dict[str, Any]] = []

    for index, upload in enumerate(files, start=1):
        candidate_id = f"Candidate-{index}"
        filename = upload.filename or f"resume-{index}.pdf"

        try:
            raw_bytes = await upload.read()
            text = _extract_pdf_text(raw_bytes)
        except Exception as exc:
            logger.exception("Failed to parse %s", filename)
            candidates.append(
                {
                    "id": candidate_id,
                    "filename": filename,
                    "error": f"Could not read PDF: {exc}",
                }
            )
            continue

        if not text:
            candidates.append(
                {
                    "id": candidate_id,
                    "filename": filename,
                    "error": "No extractable text found in PDF.",
                }
            )
            continue

        masked_text, report = mask_pii(text)

        try:
            result = ranking_graph.invoke(
                {
                    "job_description": job_description,
                    "masked_resume": masked_text,
                }
            )
        except Exception as exc:
            logger.exception("LangGraph failed for %s", filename)
            candidates.append(
                {
                    "id": candidate_id,
                    "filename": filename,
                    "error": f"Model error: {exc}",
                    "masked_resume": masked_text,
                    "masking_report": report.__dict__,
                }
            )
            continue

        analysis = result.get("analysis") or {}
        score = result.get("score") or {}

        candidates.append(
            {
                "id": candidate_id,
                "filename": filename,
                "score": int(score.get("score", 0)),
                "matched_skills": score.get("matched_skills", []),
                "missing_skills": score.get("missing_skills", []),
                "strengths": score.get("strengths", ""),
                "gaps": score.get("gaps", ""),
                "summary": analysis.get("summary", ""),
                "skills": analysis.get("skills", []),
                "years_experience": analysis.get("years_experience", 0),
                "education_level": analysis.get("education_level", "Unknown"),
                "masked_resume": masked_text,
                "masking_report": report.__dict__,
            }
        )

    # Sort: scored candidates desc by score, then errored candidates last.
    def _sort_key(c: dict[str, Any]) -> tuple[int, int]:
        if "error" in c:
            return (1, 0)
        return (0, -int(c.get("score", 0)))

    candidates.sort(key=_sort_key)

    return {
        "job_description": job_description,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
