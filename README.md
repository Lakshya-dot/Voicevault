# VoiceVault

**Meeting memory for how Indian teams actually talk.**
Upload team calls in Tanglish / Hinglish / English, then ask questions by typing or by voice.
Every answer comes with the exact transcript line and the audio moment that proves it.

Built for the Great Indian AI Internship Challenge by Gnani.ai.

## What it does
- **Transcribes** meeting recordings with timestamps (and optional speaker labels).
- **Extracts** decisions, tasks (owner + deadline) and open questions from each meeting.
- **Answers questions across all meetings** and cites the supporting lines. Any citation that
  does not match a real transcript line is automatically removed.
- **Plays the evidence**: click a citation to hear the exact moment in the recording.
- **Voice in, voice out**: ask by microphone, hear the answer spoken back.
- **Timeline & commitments**: everything decided or promised, across meetings, in date order.

## Gnani models used
| Model | Used for |
|---|---|
| Prisma v2.5 (Batch STT) | Timestamped transcripts of meeting recordings (code-mixed speech, optional denoise and speaker labels) |
| Prisma v2.5 (REST STT) | Voice questions in the app |
| Timbre v2.5 (TTS) | Spoken answers |

An external LLM (Gemini or Claude, set in `.env`) reads the transcripts for extraction and question answering.

## Architecture
```
audio -> Gnani Prisma (Batch STT) -> transcript JSON -> SQLite
voice question -> Gnani Prisma (REST STT) -> question
question + all transcripts -> LLM -> cited answer -> citations verified against the database
answer -> Gnani Timbre (TTS) -> spoken reply
Streamlit UI: Ask / Timeline & commitments / Meetings
```

## Run it
```
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```
Create a `.env` file (never commit it):
```
GNANI_API_KEY=your-gnani-key
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
LLM_MODEL=your-model-name        # run: python check_llm.py --models
```
Try it with the bundled demo meetings (no audio needed):
```
python load_samples.py
python extract.py
streamlit run app.py
```
With your own recordings:
```
python batch_transcribe.py meeting1.m4a --bias MongoDB,PostgreSQL --speakers 2
python ingest.py transcripts/meeting1.json --audio meeting1.m4a --title "Mon 2 Nov - Sprint planning" --date 2026-11-02 --names "1=Ravi,2=Priya"
python extract.py
streamlit run app.py
```

## Data
All demo recordings are synthetic: scripted meetings recorded by the team. No real calls or personal data.

## Limitations
- Speech recognition errors remain on code-mixed words; the LLM compensates in most cases but not all.
- The whole transcript set is sent to the LLM, which suits a handful of short meetings, not hundreds of hours.
- Voice questions are limited to 30 seconds.

## Team
Built by Lakshya Yarlagadda and Laasya Yarlagadda.
