"""Load a Gnani Batch transcript JSON (from batch_transcribe.py) into the database.

Usage:
  python ingest.py transcripts/meeting1.json --audio meeting1.m4a \
      --title "Mon 2 Nov - Sprint planning" --date 2026-11-02 --names "1=Ravi,2=Priya"
"""
import argparse
import json
import os
import shutil
import sys

import db


def load_segments(data, names=None):
    names = names or {}
    raw = data.get("segments") or []
    ids = {s.get("speaker_id") for s in raw if s.get("speaker_id") is not None}
    segs = []
    for s in raw:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        sid = s.get("speaker_id")
        if sid is None or (len(ids) <= 1 and str(sid) not in names):
            speaker = ""
        else:
            speaker = names.get(str(sid), f"Speaker {sid}")
        segs.append({"start": float(s.get("start_time") or 0),
                     "end": float(s.get("end_time") or 0),
                     "speaker": speaker, "text": text})
    if not segs and data.get("full_transcript"):
        segs.append({"start": 0.0, "end": float(data.get("duration_seconds") or 0),
                     "speaker": "", "text": data["full_transcript"].strip()})
    return segs


def ingest(json_path, title, date, audio=None, names=None, replace=False):
    db.init()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    existing = db.find_meeting_by_title(title)
    if existing:
        if not replace:
            print(f"'{title}' already exists (id {existing['id']}). Use --replace to overwrite.")
            return existing["id"]
        db.delete_meeting(existing["id"])
    segs = load_segments(data, names)
    if not segs:
        sys.exit("No transcript text found in that JSON file.")
    audio_path = None
    if audio:
        os.makedirs("audio", exist_ok=True)
        audio_path = os.path.join("audio", os.path.basename(audio))
        if os.path.abspath(audio) != os.path.abspath(audio_path):
            shutil.copy2(audio, audio_path)
    mid = db.add_meeting(title, date, audio_path, data.get("language_code"),
                         data.get("duration_seconds"), segs)
    print(f"Saved meeting {mid}: '{title}' with {len(segs)} segments"
          + ("" if audio_path else " (no audio)"))
    return mid


def parse_names(s):
    out = {}
    for part in (s or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("json_path")
    p.add_argument("--audio")
    p.add_argument("--title", required=True)
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--names", default="", help='speaker names, e.g. "1=Ravi,2=Priya"')
    p.add_argument("--replace", action="store_true")
    a = p.parse_args()
    ingest(a.json_path, a.title, a.date, a.audio, parse_names(a.names), a.replace)
