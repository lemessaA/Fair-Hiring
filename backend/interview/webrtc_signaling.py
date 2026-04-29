"""WebRTC signaling stub for serverless deployment.

The real-time WebRTC peer connection feature requires a persistent server
process (aiortc) which is incompatible with Vercel's serverless runtime.
This module provides no-op stubs so the rest of the interview code can
import ``webrtc_signaling`` without errors.  The ``/interview/{id}/webrtc/offer``
route in ``routes.py`` returns a clear 501 status instead.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("fair-hiring.interview.webrtc")

_UNAVAILABLE_MSG = (
    "WebRTC peer connections are not supported in the serverless deployment. "
    "Use the audio-upload submission flow instead."
)


async def create_answer_for_offer(session_id: str, sdp: str, sdp_type: str) -> dict[str, str]:
    raise RuntimeError(_UNAVAILABLE_MSG)


async def close_peer(session_id: str) -> None:
    """No-op: no persistent peers in serverless."""
    pass
