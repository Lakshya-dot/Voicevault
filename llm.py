"""One function, call_llm(), used for extraction and Q&A.

Pick the provider in .env:
  LLM_PROVIDER=gemini             (needs GEMINI_API_KEY; optional LLM_MODEL)
  LLM_PROVIDER=anthropic          (default; needs ANTHROPIC_API_KEY)
  LLM_PROVIDER=openai             (any OpenAI-compatible API; needs LLM_API_KEY,
                                   LLM_MODEL and optionally LLM_BASE_URL)
Optional: LLM_MODEL to override the default model,
  LLM_REASONING_EFFORT (openai mode only, e.g. low).
"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def _post(url, headers, payload):
    last = ""
    for attempt in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.RequestException as e:
            last = str(e)
        else:
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:500]}"
            if r.status_code not in (429, 500, 502, 503, 504, 529):
                break
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"LLM request failed. {last}")


def call_llm(system, user, max_tokens=4000):
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "gemini":
        # Native Gemini endpoint. New "AQ." keys from AI Studio work here
        # (they are often rejected on the OpenAI-compatible endpoint).
        key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing in .env")
        model = os.getenv("LLM_MODEL", "gemini-2.5-flash").replace("models/", "")
        base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        data = _post(
            f"{base}/models/{model}:generateContent",
            {"x-goog-api-key": key, "Content-Type": "application/json"},
            {"systemInstruction": {"parts": [{"text": system}]},
             "contents": [{"role": "user", "parts": [{"text": user}]}]},
        )
        cands = data.get("candidates") or []
        parts = (cands[0].get("content") or {}).get("parts", []) if cands else []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text:
            reason = (cands[0].get("finishReason") if cands
                      else (data.get("promptFeedback") or {}).get("blockReason"))
            raise RuntimeError(f"Gemini returned no text (reason: {reason}). Try again.")
        return text

    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing in .env")
        model = os.getenv("LLM_MODEL", "claude-haiku-5-5")
        data = _post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            {"model": model, "max_tokens": max_tokens, "system": system,
             "messages": [{"role": "user", "content": user}]},
        )
        text = "".join(b.get("text", "") for b in data.get("content", []))
        if not text:
            raise RuntimeError("The model returned an empty answer. Try again.")
        return text

    if provider in ("openai", "openai_compat"):
        key = os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL")
        if not key or not model:
            raise RuntimeError("LLM_API_KEY and LLM_MODEL must be set in .env")
        base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        payload = {"model": model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        effort = os.getenv("LLM_REASONING_EFFORT")  # optional, e.g. low (Gemini thinking models)
        if effort:
            payload["reasoning_effort"] = effort
        data = _post(
            f"{base}/chat/completions",
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            payload,
        )
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content")
        if not text:
            raise RuntimeError("The model returned an empty answer. Try again, or set "
                               "LLM_REASONING_EFFORT=low in .env if you use a thinking model.")
        return text

    raise RuntimeError(f"Unknown LLM_PROVIDER '{provider}' (use gemini, anthropic or openai)")
