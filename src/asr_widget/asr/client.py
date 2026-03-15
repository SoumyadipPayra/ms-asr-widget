from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)


class ASRClient:
    """WebSocket client for the ms-asr-gateway.

    Manages connecting, streaming audio, and receiving transcripts.
    Follows the gateway's WebSocket protocol:
      - Text: {"type": "start", "config": {...}}
      - Binary: raw PCM audio chunks
      - Text: {"type": "stop"}
      - Receives: {"type": "transcript", "text": "...", ...}
    """

    def __init__(
        self,
        gateway_url: str,
        sample_rate: int = 16000,
        on_transcript: Callable[[str], None] | None = None,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
        self._url = gateway_url
        self._sample_rate = sample_rate
        self._on_transcript = on_transcript
        self._on_state_change = on_state_change
        self._ws: ClientConnection | None = None
        self._receiver_task: asyncio.Task | None = None
        self._session_id: str | None = None

    @property
    def session_id(self) -> str | None:
        return self._session_id

    async def start_session(self) -> bool:
        """Connect and start a recognition session. Returns True on success."""
        try:
            self._ws = await websockets.connect(self._url)
        except Exception:
            logger.exception("Failed to connect to %s", self._url)
            self._notify_state("error")
            return False

        start_msg = json.dumps({
            "type": "start",
            "config": {
                "sample_rate": self._sample_rate,
                "encoding": "pcm_s16le",
                "channels": 1,
            },
        })
        await self._ws.send(start_msg)

        try:
            resp = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=10.0))
        except (asyncio.TimeoutError, Exception):
            logger.exception("Failed to receive start response")
            await self._close_ws()
            self._notify_state("error")
            return False

        if resp.get("type") != "started":
            logger.error("Unexpected start response: %s", resp)
            await self._close_ws()
            self._notify_state("error")
            return False

        self._session_id = resp.get("session_id")
        logger.info("ASR session started: %s", self._session_id)

        # Start receiving transcripts in the background
        self._receiver_task = asyncio.create_task(self._receive_loop())
        self._notify_state("listening")
        return True

    async def send_audio(self, chunk: bytes) -> None:
        """Send a binary audio chunk."""
        if self._ws is not None:
            try:
                await self._ws.send(chunk)
            except Exception:
                logger.warning("Failed to send audio chunk")

    async def stop_session(self) -> None:
        """Stop the recognition session gracefully."""
        if self._ws is None:
            return

        try:
            await self._ws.send(json.dumps({"type": "stop"}))
        except Exception:
            pass

        # Wait for receiver to finish (it exits on "stopped" message)
        if self._receiver_task is not None:
            try:
                await asyncio.wait_for(self._receiver_task, timeout=30.0)
            except asyncio.TimeoutError:
                self._receiver_task.cancel()
            self._receiver_task = None

        await self._close_ws()
        self._session_id = None
        self._notify_state("idle")
        logger.info("ASR session stopped")

    async def _receive_loop(self) -> None:
        """Receive and dispatch messages from the gateway."""
        if self._ws is None:
            return
        try:
            async for raw in self._ws:
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "transcript":
                    text = data.get("text", "")
                    if text and self._on_transcript is not None:
                        self._on_transcript(text)
                    self._notify_state("listening")

                elif msg_type == "stopped":
                    logger.debug("Received stopped message")
                    break

                elif msg_type == "error":
                    logger.error("Server error: %s", data.get("message"))
                    self._notify_state("error")
                    break

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception:
            logger.exception("Error in receive loop")

    async def _close_ws(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    def _notify_state(self, state: str) -> None:
        if self._on_state_change is not None:
            self._on_state_change(state)
