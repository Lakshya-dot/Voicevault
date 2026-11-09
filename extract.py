"""Use the LLM to pull decisions, tasks and open questions out of each meeting.

Usage:
  python extract.py            # meetings that have no items yet
  python extract.py --force    # redo all meetings
"""
import argparse
import json
import re

import db
import llm

SYSTEM = """You extract structured notes from one meeting transcript. The transcript is \
code-mixed (Tamil or Hindi with English, written in Latin script) and comes from speech \
recognition, so it has errors; infer the intended meaning. Use ONLY the transcript. \
Return ONLY valid JSON (no markdown) in exactly this shape:
{"decisions":[{"text":"...","segments":[12,13]}],
 "tasks":[{"text":"...","owner":"name or null","deadline":"as stated or null","segments":[14]}],
 "open_questions":[{"text":"...","segments":[15]}]}
"segments" lists the numbers N of the transcript lines [S N] that support the item. \
Write every "text" in clear English. Do not invent anything not in the transcript."""


def build_transcript(segs):
    lines = []
    for s in segs:
        who = f"{s['speaker']}: " if s["speaker"] else ""
        lines.append(f"[S{s['id']}] {db.fmt_time(s['start'])} {who}{s['text']}")
    return "\n".join(lines)


def parse_json(text):
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[a : b + 1])


def _valid_ids(raw_ids, valid):
    out = []
    for x in raw_ids or []:
        m = re.search(r"\d+", str(x))
        if m and int(m.group()) in valid and int(m.group()) not in out:
            out.append(int(m.group()))
    return out


def extract_meeting(mid):
    segs = db.get_segments(mid)
    if not segs:
        return 0
    valid = {s["id"] for s in segs}
    prompt = "TRANSCRIPT:\n" + build_transcript(segs)
    data = None
    for attempt in range(2):
        raw = llm.call_llm(SYSTEM, prompt if attempt == 0 else prompt + "\n\nReturn valid JSON only.")
        try:
            data = parse_json(raw)
            break
        except (ValueError, json.JSONDecodeError):
            continue
    if data is None:
        raise RuntimeError("The model did not return valid JSON twice. Try again.")
    items = []
    for key, kind in (("decisions", "decision"), ("tasks", "task"), ("open_questions", "question")):
        for it in data.get(key) or []:
            text = str(it.get("text") or "").strip()
            if not text:
                continue
            owner = it.get("owner")
            deadline = it.get("deadline")
            items.append({
                "kind": kind, "text": text,
                "owner": None if owner in (None, "", "null") else str(owner),
                "deadline": None if deadline in (None, "", "null") else str(deadline),
                "segments": _valid_ids(it.get("segments"), valid),
            })
    db.save_items(mid, items)
    return len(items)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    db.init()
    for m in db.list_meetings():
        if db.get_items(m["id"]) and not a.force:
            print(f"Skipping '{m['title']}' (already extracted)")
            continue
        n = extract_meeting(m["id"])
        print(f"'{m['title']}': {n} items")
