# Submission kit (fill the [BRACKETS] with your REAL results before posting)

## 1. Written explanation
**Project:** VoiceVault, meeting memory for how Indian teams actually talk.

**Problem:** Teams decide things in meetings, then nobody remembers why or who promised what.
Notes tools summarise one meeting at a time and rarely handle Tanglish/Hinglish.

**What it does:** Upload recordings of team meetings. VoiceVault transcribes them, pulls out decisions,
tasks and open questions, and lets you ask questions across all meetings by typing or by voice.
Every answer shows the transcript line and plays the exact audio moment as proof. Answers can be spoken back.

**Gnani models used:**
- Prisma v2.5 speech-to-text (Batch API) for timestamped transcripts of code-mixed meeting audio
- Prisma v2.5 speech-to-text (REST) for voice questions
- Timbre v2.5 text-to-speech for spoken answers
[Delete any line you did not actually use.]

**How it works:** Python, SQLite and Streamlit. An LLM extracts structured notes and answers questions only from
the provided transcripts. Citations are verified in code, and any that do not match a real transcript line are removed.

**What we tested:** [3] scripted Tanglish meetings recorded by us on a phone with background noise.
[X] of 8 test questions were answered correctly with correct citations. [Y] failed: [say which and why].
Prisma got most code-mixed words right; typical errors were [example, e.g. "MongoDB" heard as "mong dbu"].
We used word boosting to reduce this.

**Data:** all recordings are synthetic, recorded by the team. No real calls.

**Limitations:** [be honest: ASR errors on technical words, small dataset, 30-second voice questions].

**What's next:** longer meetings with retrieval, more Indian languages, speaker names from voice.

**Team:** [Name 1] and [Name 2] (two-person team).

## 2. LinkedIn post
Meetings end, decisions get made, and a week later nobody remembers why.

We built VoiceVault: meeting memory for how Indian teams actually talk (Tanglish, Hinglish, English). Ask a question by voice, hear the answer, and see the exact transcript line and audio moment that proves it.

Built with Gnani's Prisma speech-to-text for code-mixed speech [and Timbre for voice replies].

Demo: [video]
Code: [GitHub link]

Built by [teammate tag] and me for the Great Indian AI Internship Challenge by @Gnani.ai
#GnaniAI #GreatIndianAIInternshipChallenge

## 3. X (Twitter) post
Ask your meetings by voice. VoiceVault turns Tanglish/Hinglish team calls into searchable memory, with answers that play the exact audio moment as proof. Built with Gnani Prisma + Timbre. #GnaniAI #GreatIndianAIInternshipChallenge [video]

## 4. 60-second demo outline
0-8 s    "Three meetings, one decision, nobody remembers why." Show the Meetings tab.
8-22 s   Show a Tanglish meeting and its Gnani transcript.
22-45 s  Ask BY VOICE: "Why did we switch from MongoDB to PostgreSQL?" Show the spoken answer and the evidence.
45-55 s  Click a citation, play the exact audio moment. Flash the Timeline tab.
55-60 s  Tagline + hashtags.

## 5. Before you post
- [ ] Video is public, about 60 s, posts use BOTH hashtags
- [ ] Posts are public and nominated for verification
- [ ] GitHub repo is public and `git status` never listed .env
- [ ] Explanation lists only Gnani models you really used
- [ ] No API key visible in the video (do not open .env on screen)
