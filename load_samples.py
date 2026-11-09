"""Load 3 ready-made demo meetings (no audio) so you can test the whole pipeline
before recording anything.   python load_samples.py"""
from ingest import ingest

names = {"1": "Ravi", "2": "Priya"}
ingest("sample_transcripts/meeting1.json", "Mon 2 Nov - Sprint planning", "2026-11-02", None, names, True)
ingest("sample_transcripts/meeting2.json", "Wed 4 Nov - Check-in", "2026-11-04", None, names, True)
ingest("sample_transcripts/meeting3.json", "Fri 6 Nov - Decision meeting", "2026-11-06", None, names, True)
