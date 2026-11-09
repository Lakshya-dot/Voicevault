"""VoiceVault web app.  Run with:  streamlit run app.py"""
import hashlib
import os
import re

import streamlit as st

import ask as ask_mod
import db
import extract as extract_mod
import gnani_voice as gv

st.set_page_config(page_title="VoiceVault", page_icon="🎙️", layout="wide")
db.init()

MIME = {".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".wav": "audio/wav",
        ".ogg": "audio/ogg", ".flac": "audio/flac", ".aac": "audio/aac"}


@st.cache_data
def load_audio(path):
    with open(path, "rb") as f:
        return f.read()


def play(path, start=0):
    if path and os.path.exists(path):
        mime = MIME.get(os.path.splitext(path)[1].lower(), "audio/wav")
        st.audio(load_audio(path), format=mime, start_time=int(start))
    else:
        st.caption("Audio file not available for this meeting.")


def set_pos(key, start):
    st.session_state[key] = start


def tag(seg):
    return f"{seg['date']} {db.fmt_time(seg['start'])}"


st.title("🎙️ VoiceVault")
st.caption("Your meetings, remembered. Every answer shows the transcript line and audio moment behind it.")

meetings = db.list_meetings()
if not meetings:
    st.info("No meetings yet. Run `python load_samples.py` (demo data) or `python ingest.py ...` first.")
    st.stop()

with st.sidebar:
    st.subheader("Meetings")
    for m in meetings:
        st.write(f"**{m['title']}**  \n{m['date']}")

tab_ask, tab_time, tab_meet = st.tabs(["Ask your meetings", "Timeline & commitments", "Meetings"])

# ---------------------------------------------------------------- Ask
def ask_and_store(question, via_voice=False):
    st.session_state["voice_reply"] = None
    st.session_state["voice_error"] = None
    with st.spinner("Searching your meetings..."):
        try:
            st.session_state["result"] = ask_mod.answer(question)
        except Exception as e:  # show the problem instead of crashing
            st.session_state["result"] = None
            st.error(f"Could not get an answer: {e}")
            return
    if via_voice:
        make_voice_reply()


def make_voice_reply():
    res = st.session_state.get("result")
    if not res:
        return
    try:
        st.session_state["voice_reply"] = gv.synthesize(gv.speakable(res["answer"]))
        st.session_state["voice_error"] = None
        st.session_state["autoplay_once"] = True
    except Exception as e:
        st.session_state["voice_error"] = str(e)


with tab_ask:
    q = st.text_input("Ask anything across all your meetings",
                      placeholder="Why did we switch from MongoDB to PostgreSQL, and who suggested it?")
    if st.button("Ask", type="primary") and q.strip():
        st.session_state["heard"] = None
        ask_and_store(q.strip())

    st.markdown("**Or ask by voice** (Tanglish, Hinglish or English, up to 30 seconds)")
    recording = st.audio_input("Record your question")
    if recording is not None:
        data = recording.getvalue()
        digest = hashlib.md5(data).hexdigest()
        if st.session_state.get("last_audio") != digest:  # only handle each recording once
            st.session_state["last_audio"] = digest
            try:
                with st.spinner("Listening (Gnani Prisma)..."):
                    heard = gv.transcribe(data)
                st.session_state["heard"] = heard
                ask_and_store(heard, via_voice=True)
            except Exception as e:
                st.session_state["heard"] = None
                st.error(str(e))
    if st.session_state.get("heard"):
        st.caption(f"Heard: \u201c{st.session_state['heard']}\u201d")

    res = st.session_state.get("result")
    if res:
        by_id = {c["id"]: c for c in res["citations"]}
        text = re.sub(r"\[S(\d+)\]",
                      lambda m: f" `[{tag(by_id[int(m.group(1))])}]`" if int(m.group(1)) in by_id else "",
                      res["answer"])
        st.markdown("### Answer")
        st.markdown(text)

        reply = st.session_state.get("voice_reply")
        if reply:
            once = st.session_state.pop("autoplay_once", False)
            try:
                st.audio(reply, format="audio/mpeg", autoplay=once)
            except TypeError:
                st.audio(reply, format="audio/mpeg")
        else:
            st.button("\U0001F50A Speak this answer (Gnani Timbre)", on_click=make_voice_reply)
        if st.session_state.get("voice_error"):
            st.warning(st.session_state["voice_error"])

        if res["citations"]:
            st.markdown("### Evidence")
        for c in res["citations"]:
            with st.container(border=True):
                who = f" \u00b7 {c['speaker']}" if c["speaker"] else ""
                st.markdown(f"**{c['title']}** \u00b7 {c['date']} \u00b7 \u23f1 {db.fmt_time(c['start'])}{who}")
                st.write(f"\u201c{c['text']}\u201d")
                play(c["audio_path"], c["start"])
        if res["removed"]:
            st.caption(f"{len(res['removed'])} citation(s) that matched no transcript line were removed.")

# ------------------------------------------------------------ Timeline
with tab_time:
    st.caption("Everything decided, promised or left open, across all meetings, in date order.")
    missing = [m for m in meetings if not db.get_items(m["id"])]
    if missing:
        st.info(f"{len(missing)} meeting(s) have not been analysed yet.")
        if st.button("Extract decisions & tasks from all meetings", type="primary", key="ex_all"):
            with st.spinner("Reading your meetings..."):
                try:
                    for m in missing:
                        extract_mod.extract_meeting(m["id"])
                    st.rerun()
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

    KINDS = {"Decisions": "decision", "Tasks": "task", "Open questions": "question"}
    ICON = {"decision": "\u2705", "task": "\U0001F4CC", "question": "\u2753"}
    shown = st.multiselect("Show", list(KINDS), default=list(KINDS))
    wanted = {KINDS[k] for k in shown}
    all_segs = {s["id"]: s for s in db.get_segments()}

    tasks = [dict(Task=i["text"], Owner=i["owner"] or "-", Due=i["deadline"] or "-",
                  Meeting=f"{m['date']} {m['title']}")
             for m in meetings for i in db.get_items(m["id"]) if i["kind"] == "task"]
    if tasks and "task" in wanted:
        st.markdown("##### Commitments")
        st.dataframe(tasks, hide_index=True)

    for m in meetings:
        items = [i for i in db.get_items(m["id"]) if i["kind"] in wanted]
        if not items:
            continue
        st.markdown(f"#### {m['date']} \u00b7 {m['title']}")
        for it in items:
            extra = []
            if it["owner"]:
                extra.append(f"owner: {it['owner']}")
            if it["deadline"]:
                extra.append(f"due: {it['deadline']}")
            st.markdown(f"{ICON[it['kind']]} {it['text']}" + (f"  _({', '.join(extra)})_" if extra else ""))
            proof = [all_segs[i] for i in it["seg_ids"] if i in all_segs][:2]
            if proof:
                with st.expander("Evidence"):
                    for sg in proof:
                        st.write(f"\u201c{sg['text']}\u201d \u00b7 \u23f1 {db.fmt_time(sg['start'])}")
                        play(m["audio_path"], sg["start"])

# ------------------------------------------------------------ Meetings
with tab_meet:
    labels = {m["id"]: f"{m['date']} · {m['title']}" for m in meetings}
    mid = st.selectbox("Meeting", list(labels), format_func=lambda i: labels[i])
    m = db.get_meeting(mid)
    segs = db.get_segments(mid)
    seg_by_id = {s["id"]: s for s in segs}
    pos_key = f"pos_{mid}"

    st.markdown(f"#### {m['title']}")
    play(m["audio_path"], st.session_state.get(pos_key, 0))
    st.caption("Click a ▶ time to jump the player there, then press play.")

    left, right = st.columns([3, 2])
    with left:
        st.markdown("##### Transcript")
        for s in segs:
            c1, c2 = st.columns([1, 7])
            c1.button(f"▶ {db.fmt_time(s['start'])}", key=f"seg_{s['id']}",
                      on_click=set_pos, args=(pos_key, s["start"]))
            who = f"**{s['speaker']}:** " if s["speaker"] else ""
            c2.markdown(f"{who}{s['text']}")

    with right:
        st.markdown("##### Decisions, tasks & open questions")
        items = db.get_items(mid)
        if not items:
            if st.button("Extract with AI", type="primary", key=f"ex_{mid}"):
                with st.spinner("Reading the meeting..."):
                    try:
                        extract_mod.extract_meeting(mid)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Extraction failed: {e}")
        for kind, title in (("decision", "Decisions"), ("task", "Tasks"), ("question", "Open questions")):
            group = [i for i in items if i["kind"] == kind]
            if not group:
                continue
            st.markdown(f"**{title}**")
            for it in group:
                extra = []
                if it["owner"]:
                    extra.append(f"owner: {it['owner']}")
                if it["deadline"]:
                    extra.append(f"due: {it['deadline']}")
                st.markdown(f"- {it['text']}" + (f"  _({', '.join(extra)})_" if extra else ""))
                for sid in it["seg_ids"]:
                    if sid in seg_by_id:
                        st.button(f"▶ {db.fmt_time(seg_by_id[sid]['start'])}",
                                  key=f"it_{it['id']}_{sid}", on_click=set_pos,
                                  args=(pos_key, seg_by_id[sid]["start"]))
