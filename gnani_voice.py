"""Gnani speech helpers: Prisma speech-to-text (REST, clips up to 30 s) and
Timbre text-to-speech (REST, returns an MP3).

Optional .env settings (all have defaults):
  GNANI_STT_LANG=en-IN        language of spoken questions (en-IN reads Tanglish/Hinglish best)
  GNANI_STT_MODEL=            leave empty for Prisma v2.5, or prisma-v3.0
  GNANI_TTS_MODEL=timbre-v2.5   (or timbre-v3.0)
  GNANI_TTS_VOICE=Kaveri        (voice names differ per model, see the Voice Catalog)
  GNANI_TTS_LANG=en-IN
"""
import io
import os
import re
import time
import wave

import requests
from dotenv import load_dotenv

import llm

load_dotenv()
BASE = os.getenv("GNANI_BASE_URL", "https://api.vachana.ai").rstrip("/")


def _key():
    k = os.getenv("GNANI_API_KEY")
    if not k or k.startswith("paste-your"):
        raise RuntimeError("GNANI_API_KEY is missing in .env")
    return k


def _explain(r):
    """Turn a Gnani error response into one readable sentence."""
    try:
        b = r.json()
    except ValueError:
        return f"HTTP {r.status_code}: {r.text[:200]}"
    detail = b.get("detail")
    if isinstance(detail, dict):
        msg = detail.get("message") or detail.get("error_code")
    else:
        err = b.get("error")
        msg = (err.get("message") if isinstance(err, dict) else None) or b.get("message")
    return f"HTTP {r.status_code}: {msg or str(b)[:200]}"


def _request(url, **kw):
    headers = {"X-API-Key-ID": _key()}
    headers.update(kw.pop("headers", {}))
    r = None
    for attempt in range(3):
        r = requests.post(url, headers=headers, timeout=90, **kw)
        if r.status_code != 429:
            break
        time.sleep(3 * (attempt + 1))
    if r.status_code == 402:
        raise RuntimeError("Gnani says you are out of credits (HTTP 402). Check Usage in the dashboard.")
    return r


def wav_seconds(data):
    """Length of a WAV clip in seconds, or None if it isn't a readable WAV."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


def transcribe(audio_bytes, filename="question.wav", language=None):
    secs = wav_seconds(audio_bytes)
    if secs is not None and secs > 29.5:
        raise RuntimeError(f"That recording is {secs:.0f} s. Voice questions must be under 30 seconds.")
    data = {"language_code": language or os.getenv("GNANI_STT_LANG", "en-IN")}
    if os.getenv("GNANI_STT_MODEL"):
        data["model"] = os.getenv("GNANI_STT_MODEL")
    r = _request(f"{BASE}/stt/v3", files={"audio_file": (filename, audio_bytes)}, data=data)
    try:
        body = r.json()
    except ValueError:
        raise RuntimeError(_explain(r))
    if r.status_code != 200 or not body.get("success"):
        raise RuntimeError("Speech recognition failed. " + _explain(r))
    text = (body.get("transcript") or "").strip()
    if not text:
        raise RuntimeError("I couldn't hear anything in that recording. Try again, closer to the mic.")
    return text


def speakable(answer, max_chars=420):
    """Short, plain version of an answer for text-to-speech (no citations or markdown;
    numbers and dates written as words, as Gnani recommends)."""
    clean = re.sub(r"\[S\d+\]", "", answer)
    clean = re.sub(r"[*_`#>]+", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    clean = re.sub(r"\s+([.,?!])", r"\1", clean)
    try:
        out = llm.call_llm(
            "Rewrite the answer as at most two short, natural spoken sentences in English. "
            "Plain text only: no markdown, no lists, no citations. Write numbers and dates "
            "as spoken words (for example 'fourth of November'). Keep names and facts unchanged.",
            clean, max_tokens=300).strip()
        if out:
            clean = out
    except Exception:
        pass  # fall back to the cleaned answer
    if len(clean) > max_chars:
        cut = clean[:max_chars]
        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        clean = cut[: end + 1] if end > 80 else cut.rsplit(" ", 1)[0] + "."
    return clean


def synthesize(text):
    """Return MP3 bytes of `text` spoken with Gnani Timbre."""
    payload = {
        "text": text,
        "voice": os.getenv("GNANI_TTS_VOICE", "Kaveri"),
        "model": os.getenv("GNANI_TTS_MODEL", "timbre-v2.5"),
        "language": os.getenv("GNANI_TTS_LANG", "en-IN"),
        "speed": 1.0,
        "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                         "container": "mp3", "bitrate": "64k"},
    }
    r = _request(f"{BASE}/api/v1/tts/inference", json=payload)
    ctype = r.headers.get("Content-Type", "")
    if r.status_code != 200 or ctype.startswith("application/json"):
        raise RuntimeError("Voice generation failed. " + _explain(r))
    return r.content
