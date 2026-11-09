"""Tests your AI-model setup (the key used for questions and extraction).

  python check_llm.py            # sends one tiny test message
  python check_llm.py --models   # lists model names your key can use (gemini / openai)

Never prints your key.
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()
import llm  # noqa: E402

provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
print("Provider:", provider, "| Model:", os.getenv("LLM_MODEL") or "(default)")


def list_models():
    key = os.getenv("LLM_API_KEY")
    base = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if not key:
        sys.exit("LLM_API_KEY is missing in .env")
    r = requests.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Could not list models (HTTP {r.status_code}): {r.text[:300]}")
    ids = sorted({m.get("id", "").replace("models/", "") for m in r.json().get("data", [])})
    ids = [i for i in ids if i]
    chat_like = [i for i in ids if "embed" not in i and "image" not in i and "tts" not in i]
    print("\nModel names you can put in LLM_MODEL (flash / flash-lite are fast and cheap):")
    for i in (chat_like or ids)[:80]:
        print("  ", i)


def list_models_gemini():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    if not key:
        sys.exit("GEMINI_API_KEY is missing in .env")
    r = requests.get(f"{base}/models", headers={"x-goog-api-key": key},
                     params={"pageSize": 200}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Could not list models (HTTP {r.status_code}): {r.text[:300]}")
    ids = sorted(m["name"].replace("models/", "") for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", []))
    print("\nModel names you can put in LLM_MODEL (flash / flash-lite are fast and cheap):")
    for i in ids:
        print("  ", i)


if "--models" in sys.argv:
    if provider == "gemini":
        list_models_gemini()
        sys.exit(0)
    if provider == "anthropic":
        sys.exit("--models is for LLM_PROVIDER=openai. For Claude, the default model is used.")
    list_models()
    sys.exit(0)

try:
    reply = llm.call_llm("Reply with the single word OK.", "ping", max_tokens=300)
    print("\nSUCCESS. Model replied:", reply.strip()[:80])
    print("Now restart the app:  streamlit run app.py")
except Exception as e:
    print("\nFAILED:", e)
    if provider in ("gemini", "openai"):
        print("\nIf it says 404 or 'model not found', run:  python check_llm.py --models")
        print("and copy one of the names into LLM_MODEL in .env.")
    sys.exit(1)
