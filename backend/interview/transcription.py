from __future__ import annotations

import io
import logging
import os
from typing import Protocol

import httpx

logger = logging.getLogger("fair-hiring.interview.transcription")


class Transcriber(Protocol):
    async def transcribe(self, audio_bytes: bytes, filename: str, mime: str) -> str: ...


class MockTranscriber:
    """Deterministic placeholder transcript for demos without STT."""

    async def transcribe(self, audio_bytes: bytes, filename: str, mime: str) -> str:
        n = len(audio_bytes)
        return (
            f"[mock_transcription file={filename!r} bytes={n} mime={mime!r}] "
            "I led backend work on a Python FastAPI service with PostgreSQL. "
            "We improved latency by adding indexes and caching hot reads in Redis."
        )


class GroqWhisperTranscriber:
    """Groq OpenAI-compatible audio transcription API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._model = os.environ.get("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")

    async def transcribe(self, audio_bytes: bytes, filename: str, mime: str) -> str:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        files = {"file": (filename, io.BytesIO(audio_bytes), mime or "application/octet-stream")}
        data = {"model": self._model, "temperature": "0"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, data=data, files=files)
            resp.raise_for_status()
            body = resp.json()
            text = body.get("text")
            if not text:
                raise RuntimeError(f"Unexpected transcription response: {body}")
            return str(text).strip()


def get_transcriber() -> Transcriber:
    if os.environ.get("INTERVIEW_USE_GROQ_TRANSCRIPTION", "").lower() in ("1", "true", "yes"):
        key = os.environ.get("GROQ_API_KEY", "")
        if not key:
            logger.warning("INTERVIEW_USE_GROQ_TRANSCRIPTION set but GROQ_API_KEY missing; using mock.")
            return MockTranscriber()
        return GroqWhisperTranscriber(key)
    return MockTranscriber()
