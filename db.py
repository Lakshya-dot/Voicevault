"""SQLite helpers for VoiceVault."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("VV_DB", "voicevault.db")


@contextmanager
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with db() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS meetings(
                id INTEGER PRIMARY KEY, title TEXT, date TEXT,
                audio_path TEXT, language TEXT, duration REAL);
            CREATE TABLE IF NOT EXISTS segments(
                id INTEGER PRIMARY KEY, meeting_id INTEGER, idx INTEGER,
                start REAL, end REAL, speaker TEXT, text TEXT);
            CREATE TABLE IF NOT EXISTS items(
                id INTEGER PRIMARY KEY, meeting_id INTEGER, kind TEXT,
                text TEXT, owner TEXT, deadline TEXT, seg_ids TEXT);
            """
        )


def fmt_time(sec):
    sec = int(sec or 0)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def add_meeting(title, date, audio_path, language, duration, segments):
    with db() as c:
        cur = c.execute(
            "INSERT INTO meetings(title,date,audio_path,language,duration) VALUES (?,?,?,?,?)",
            (title, date, audio_path, language, duration),
        )
        mid = cur.lastrowid
        for i, s in enumerate(segments):
            c.execute(
                "INSERT INTO segments(meeting_id,idx,start,end,speaker,text) VALUES (?,?,?,?,?,?)",
                (mid, i, s["start"], s["end"], s["speaker"], s["text"]),
            )
    return mid


def find_meeting_by_title(title):
    with db() as c:
        r = c.execute("SELECT * FROM meetings WHERE title=?", (title,)).fetchone()
        return dict(r) if r else None


def delete_meeting(mid):
    with db() as c:
        c.execute("DELETE FROM items WHERE meeting_id=?", (mid,))
        c.execute("DELETE FROM segments WHERE meeting_id=?", (mid,))
        c.execute("DELETE FROM meetings WHERE id=?", (mid,))


def list_meetings():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM meetings ORDER BY date, id")]


def get_meeting(mid):
    with db() as c:
        r = c.execute("SELECT * FROM meetings WHERE id=?", (mid,)).fetchone()
        return dict(r) if r else None


def get_segments(meeting_id=None):
    """Segments (with meeting info), oldest meeting first, in spoken order."""
    q = (
        "SELECT s.id, s.meeting_id, s.idx, s.start, s.end, s.speaker, s.text,"
        " m.title, m.date, m.audio_path"
        " FROM segments s JOIN meetings m ON m.id = s.meeting_id"
    )
    args = ()
    if meeting_id is not None:
        q += " WHERE s.meeting_id=?"
        args = (meeting_id,)
    q += " ORDER BY m.date, m.id, s.idx"
    with db() as c:
        return [dict(r) for r in c.execute(q, args)]


def save_items(mid, items):
    import json

    with db() as c:
        c.execute("DELETE FROM items WHERE meeting_id=?", (mid,))
        for it in items:
            c.execute(
                "INSERT INTO items(meeting_id,kind,text,owner,deadline,seg_ids) VALUES (?,?,?,?,?,?)",
                (mid, it["kind"], it["text"], it.get("owner"), it.get("deadline"),
                 json.dumps(it.get("segments", []))),
            )


def get_items(mid):
    import json

    with db() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM items WHERE meeting_id=? ORDER BY id", (mid,))]
    for r in rows:
        r["seg_ids"] = json.loads(r["seg_ids"] or "[]")
    return rows
