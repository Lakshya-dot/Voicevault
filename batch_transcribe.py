"""
Transcribe a meeting recording with Gnani Batch STT (timestamped segments).

Usage:
    python batch_transcribe.py meeting1.m4a
    python batch_transcribe.py meeting1.m4a --bias MongoDB,PostgreSQL,Priya,Ravi,Arun
    python batch_transcribe.py meeting1.m4a --lang en-IN --speakers 2 --denoise

Output: transcripts/<name>.json  (full transcript + segments with start/end times)
Direct upload limit is 10 MB per file. If a step fails, read the printed response.
"""
import argparse
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("GNANI_API_KEY")
BASE = "https://api.vachana.ai/stt/v3/batch/jobs"
HEADERS = {"X-API-Key-ID": KEY or ""}
TERMINAL = {"COMPLETED", "PARTIAL_FAILURE", "FAILED", "START_FAILED", "CANCELLED"}


def find_urls(obj):
    """Recursively collect every 'transcript_url' value in a JSON response."""
    urls = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "transcript_url" and isinstance(v, str):
                urls.append(v)
            else:
                urls += find_urls(v)
    elif isinstance(obj, list):
        for item in obj:
            urls += find_urls(item)
    return urls


def main():
    if not KEY or KEY.startswith("paste-your"):
        sys.exit("No API key found. Put it in .env as GNANI_API_KEY=... first.")

    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("--lang", default="en-IN")
    p.add_argument("--speakers", type=int, default=0, help="turn on speaker labels; max speakers 1-8")
    p.add_argument("--denoise", action="store_true")
    p.add_argument("--bias", default="", help="comma-separated single words to boost, e.g. MongoDB,PostgreSQL")
    a = p.parse_args()

    cfg = {
        "model": "gnani-prisma-v2.5",
        "language_code": a.lang,
        "mode": "transcribe",
        "with_diarization": a.speakers > 0,
        "is_multi_channel": False,
        "with_denoise": a.denoise,
    }
    if a.speakers > 0:
        cfg["num_speakers"] = a.speakers

    # word boosting: single words, letters only (Gnani rejects anything else)
    wanted = [w.strip() for w in a.bias.split(",") if w.strip()]
    words = [w for w in wanted if w.isalpha()][:100]
    if len(words) < len(wanted):
        print("Skipped bias entries that are not single letter-only words:",
              [w for w in wanted if not w.isalpha()])
    if words:
        cfg["bias_list"] = words
        cfg["bias_score"] = 1.5

    # 1. create
    with open(a.audio, "rb") as f:
        r = requests.post(
            BASE,
            headers=HEADERS,
            files=[
                ("config", (None, json.dumps(cfg), "application/json")),
                ("files", (os.path.basename(a.audio), f)),
            ],
            timeout=300,
        )
    if r.status_code not in (200, 201):
        sys.exit(f"Create failed ({r.status_code}): {r.text}")
    job_id = r.json()["job_id"]
    print("Job created:", job_id)

    # 2. start (creating does NOT start it)
    r = requests.post(f"{BASE}/{job_id}/start", headers=HEADERS, timeout=60)
    if r.status_code not in (200, 202):
        sys.exit(f"Start failed ({r.status_code}): {r.text}")

    # 3. poll every 10 s
    while True:
        r = requests.get(f"{BASE}/{job_id}", headers=HEADERS, timeout=60)
        status = r.json().get("status")
        print("Status:", status)
        if status in TERMINAL:
            break
        time.sleep(10)
    if status not in ("COMPLETED", "PARTIAL_FAILURE"):
        sys.exit(f"Job ended with status {status}: {r.text}")

    # 4. transcript URLs expire after 1 hour, so download right away
    r = requests.get(f"{BASE}/{job_id}/files", headers=HEADERS,
                     params={"status": "COMPLETED"}, timeout=60)
    urls = find_urls(r.json())
    if not urls:
        print("No transcript_url found. Raw /files response:")
        sys.exit(json.dumps(r.json(), indent=2))

    # 5. download and save
    os.makedirs("transcripts", exist_ok=True)
    name = os.path.splitext(os.path.basename(a.audio))[0]
    data = requests.get(urls[0], timeout=120).json()
    out = os.path.join("transcripts", f"{name}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print("Saved:", out)

    for seg in data.get("segments", [])[:10]:
        print(f"[{seg.get('start_time')}-{seg.get('end_time')}] "
              f"spk{seg.get('speaker_id')}: {seg.get('text')}")


if __name__ == "__main__":
    main()
