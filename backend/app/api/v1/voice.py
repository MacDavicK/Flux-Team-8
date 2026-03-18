"""
Voice API endpoints

GET /api/v1/voice/token  — Issue short-lived Deepgram token for direct browser STT + TTS

The token is a short-lived JWT that the browser uses to call Deepgram directly:
  - STT: wss://api.deepgram.com/v1/listen  (streamed mic audio)
  - TTS: https://api.deepgram.com/v1/speak

Auth for browser WebSocket uses the Sec-WebSocket-Protocol header:
  new WebSocket(url, ["token", "<jwt>"])

The Deepgram API key never leaves the backend.
"""

from __future__ import annotations

import asyncio

from deepgram import DeepgramClient
from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/token")
@limiter.limit("10/minute")
async def get_voice_token(
    request: Request,
    current_user=Depends(get_current_user),
) -> dict:
    """Issue a short-lived Deepgram JWT for direct browser -> Deepgram STT and TTS."""
    if not settings.deepgram_api_key:
        raise HTTPException(status_code=502, detail="Voice token unavailable")

    try:
        dg_client = DeepgramClient(api_key=settings.deepgram_api_key)
        # Extend TTL from default 30s to 120s. The token is only needed for
        # the initial WebSocket handshake — the connection persists after.
        # 120s gives comfortable margin for network latency and retries.
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: dg_client.auth.v1.tokens.grant(ttl_seconds=120),
        )
        return {"token": response.access_token, "expires_in": response.expires_in}
    except Exception:
        raise HTTPException(status_code=502, detail="Voice token unavailable")
