#!/usr/bin/env python3
"""Headless integration test for the ASR widget pipeline.

Exercises: config → ASRClient → WebSocket → gateway → transcript callback,
using sample/audio1.wav from the ms-asr project (no mic, no GUI needed).
"""

import asyncio
import audioop
import logging
import sys
import wave

sys.path.insert(0, "src")

from asr_widget.config import load_config
from asr_widget.asr.client import ASRClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

WAV_PATH = "../ms-asr/sample/audio1.wav"
CHUNK_DURATION_MS = 100
TARGET_SR = 16000

transcripts: list[str] = []


def on_transcript(text: str) -> None:
    transcripts.append(text)
    print(f"  >> TRANSCRIPT: {text}")


def load_wav() -> bytes:
    with wave.open(WAV_PATH, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
        n_ch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()

    if n_ch == 2:
        raw = audioop.tomono(raw, sw, 1, 1)
    if sr != TARGET_SR:
        raw, _ = audioop.ratecv(raw, sw, 1, sr, TARGET_SR, None)
    if sw != 2:
        raw = audioop.lin2lin(raw, sw, 2)
    return raw


async def run_test() -> None:
    config = load_config()
    print(f"Gateway: {config.gateway.url}")

    client = ASRClient(
        gateway_url=config.gateway.url,
        sample_rate=TARGET_SR,
        on_transcript=on_transcript,
    )

    # Load audio
    audio = load_wav()
    chunk_size = int(TARGET_SR * 2 * CHUNK_DURATION_MS / 1000)
    print(f"Audio: {len(audio)} bytes ({len(audio) / (TARGET_SR * 2):.1f}s), chunk={chunk_size}B")

    # Start session
    print("\n--- Starting ASR session ---")
    ok = await client.start_session()
    if not ok:
        print("FAILED to start session. Is the gateway running?")
        sys.exit(1)
    print(f"Session: {client.session_id}")

    # Stream audio at ~real-time pace
    print("Streaming audio...")
    offset = 0
    while offset < len(audio):
        chunk = audio[offset : offset + chunk_size]
        await client.send_audio(chunk)
        offset += len(chunk)
        await asyncio.sleep(CHUNK_DURATION_MS / 1000.0)

    print(f"Sent {offset} bytes")

    # Stop and wait for final transcripts
    print("\n--- Stopping session ---")
    await client.stop_session()

    # Summary
    print(f"\n=== Results: {len(transcripts)} transcript(s) ===")
    for i, t in enumerate(transcripts):
        print(f"  [{i}] {t}")

    if transcripts:
        print("\nSUCCESS — end-to-end pipeline working")
    else:
        print("\nWARNING — no transcripts received")


if __name__ == "__main__":
    asyncio.run(run_test())
