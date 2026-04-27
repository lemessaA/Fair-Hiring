"""FastAPI entrypoint for the Fair Hiring Network backend.

Routes are registered without the ``/api`` prefix because Vercel's
``experimentalServices`` strips ``routePrefix`` before forwarding the
request to this service.
"""

from __future__ import annotations

import io
import logging
import os
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
from pii import mask_pii


logger = logging.getLogger("fair-hiring")
logging.basicConfig(level=logging.INFO)


app = fastapi.FastAPI(title="Fair Hiring Network API")

app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "groq_key_configured": bool(os.environ.get("GROQ_API_KEY")),
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
      3. Sent to a LangGraph workflow that calls Gemini to analyze + score it
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
