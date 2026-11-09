"""Ask a question across all meetings. Answers cite transcript lines like [S12];
every citation is checked against the database and invented ones are removed.

Usage:  python ask.py "Why did we switch from MongoDB to PostgreSQL?"
"""
import re
import sys

import db
import llm

SYSTEM = """You answer questions about a team's recorded meetings. Use ONLY the transcript \
excerpts provided. The transcripts are code-mixed (Tamil or Hindi with English, in Latin \
script) from speech recognition, so they contain errors; infer meaning carefully. \
After every claim, cite the supporting lines like [S12] or [S12][S15]. If the transcripts \
do not contain the answer, say so plainly and cite nothing. Answer in English, concisely. \
When something changed over time, explain the sequence by meeting date."""

MAX_CHARS = 150_000


def build_context(segs):
    out, current = [], None
    for s in segs:
        if s["meeting_id"] != current:
            current = s["meeting_id"]
            out.append(f"\n=== Meeting: {s['title']} ({s['date']}) ===")
        who = f"{s['speaker']}: " if s["speaker"] else ""
        out.append(f"[S{s['id']}] {db.fmt_time(s['start'])} {who}{s['text']}")
    return "\n".join(out)


def answer(question):
    segs = db.get_segments()
    if not segs:
        return {"answer": "No meetings are loaded yet.", "citations": [], "removed": []}
    by_id = {s["id"]: s for s in segs}
    ctx = build_context(segs)[-MAX_CHARS:]
    raw = llm.call_llm(SYSTEM, f"TRANSCRIPTS:\n{ctx}\n\nQUESTION: {question}")

    cited, removed = [], []

    def repl(m):
        toks = re.findall(r"S(\d+)", m.group(1))
        if not toks:
            return m.group(0)
        keep = []
        for t in toks:
            sid = int(t)
            if sid in by_id:
                keep.append(sid)
                if sid not in cited:
                    cited.append(sid)
            else:
                removed.append(sid)
        return "".join(f"[S{k}]" for k in keep)

    clean = re.sub(r"\[([^\]]*)\]", repl, raw).strip()
    return {"answer": clean, "citations": [by_id[i] for i in cited], "removed": removed}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Usage: python ask.py "your question"')
    res = answer(" ".join(sys.argv[1:]))
    print("\n" + res["answer"] + "\n")
    for c in res["citations"]:
        print(f"  [S{c['id']}] {c['title']} @ {db.fmt_time(c['start'])}: {c['text']}")
    if res["removed"]:
        print(f"\n(removed {len(res['removed'])} citation(s) that matched no transcript line)")
