"""Optional high-quality TTS (OpenAI) with local file cache.

Set environment variable OPENAI_API_KEY or pass api_key=.
Falls back to None if unavailable — UI should use Web Speech / pyttsx3.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "tts_cache"


def cache_path(text: str, voice: str = "alloy") -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(f"{voice}:{text}".encode("utf-8")).hexdigest()[:20]
    return CACHE / f"{h}.mp3"


def synthesize_openai(text: str, api_key: str | None = None, voice: str = "alloy") -> Path | None:
    """Return path to mp3 or None on failure."""
    key = api_key or os.environ.get("OPENAI_API_KEY") or ""
    if not key or not text.strip():
        return None
    out = cache_path(text, voice)
    if out.is_file() and out.stat().st_size > 0:
        return out
    try:
        import urllib.request
        import json
        body = json.dumps({
            "model": "gpt-4o-mini-tts",
            "voice": voice,
            "input": text[:4000],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/audio/speech",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if data[:4] == b"RIFF" or data[:3] == b"ID3" or data[:2] == b"\xff\xfb" or len(data) > 1000:
            out.write_bytes(data)
            return out
        # Some APIs return raw mp3 without ID3
        if len(data) > 500:
            out.write_bytes(data)
            return out
    except Exception:
        return None
    return None
