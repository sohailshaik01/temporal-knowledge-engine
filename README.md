# Temporal Knowledge Engine

An offline Python knowledge retrieval system for time-versioned website snapshots. It supports historical `as_of` queries, source citations, evidence ranking, and contradiction reporting through the hackathon's `build()` contract.

## Structure

- `submission/solution.py` — implementation of `build()`, `ingest()`, `answer()`, and `conflicts()`.
- `submission/requirements.txt` — runtime dependencies.
- `submission/NOTES.md` — implementation design, data handling, and limitations.

## Evaluation

Place `submission/` inside the participant kit root, alongside the provided `harness/`, `eval/`, and `snapshots_zip/` directories. Run:

```bash
python harness/run_eval.py --submission submission --eval eval/public_eval.jsonl
```

The current implementation is a baseline. It requires no external API keys or network calls. Additional work is needed to improve structured table extraction, evidence selection, and conflict resolution.

## Data handling

The event's website snapshots and their extracted contents are not included in this repository. Obtain the participant kit separately from the event organizers.
