"""Minimal WebRTC SDP exchange using aiortc (server answers client offer).

Does not send video to any LLM. Optional audio track handler logs receipt only;
production would pipe audio to the transcription service.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiortc import RTCPeerConnection, RTCSessionDescription

logger = logging.getLogger("fair-hiring.interview.webrtc")

_peers: dict[str, RTCPeerConnection] = {}
_lock = asyncio.Lock()


async def create_answer_for_offer(session_id: str, sdp: str, sdp_type: str) -> dict[str, str]:
    async with _lock:
        old = _peers.pop(session_id, None)
        if old is not None:
            await old.close()

        pc = RTCPeerConnection()
        _peers[session_id] = pc

        @pc.on("track")
        async def on_track(track: Any) -> None:
            logger.info("WebRTC track received session=%s kind=%s id=%s", session_id, track.kind, track.id)
            # MVP: do not buffer RTP to file here (would need MediaRecorder + disk IO).
            # Consume track to avoid backpressure issues in some clients.
            @track.on("ended")
            async def _ended() -> None:
                logger.info("Track ended session=%s kind=%s", session_id, track.kind)

        # Negotiate inbound audio from browser (recvonly).
        pc.addTransceiver("audio", direction="recvonly")

        await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=sdp_type))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        assert pc.localDescription is not None
        return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


async def close_peer(session_id: str) -> None:
    async with _lock:
        pc = _peers.pop(session_id, None)
    if pc is not None:
        await pc.close()
