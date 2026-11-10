# Temporal Knowledge Engine

An offline Python system for answering questions against dated website snapshots. It implements the participant-kit `build()`, `ingest()`, `answer()`, and `conflicts()` contract.

## Components

- `submission/solution.py` — snapshot ingestion, indexed retrieval, historical selection, answer citations, and conflict reporting
- `submission/facts.py` — typed rate-table extraction, product and tier matching, and effective-date metadata
- `submission/requirements.txt` — standard-library-only runtime
- `submission/NOTES.md` — implementation decisions and limitations
- `tests/test_facts.py` — standalone synthetic rate-table tests
- `tests/test_temporal.py` — contract tests requiring the supplied participant harness

## Setup and evaluation

Use Python 3.11 or newer. Place the repository contents in the participant kit root so that `harness/`, `eval/`, and `snapshots_zip/` are siblings of `submission/`. No API keys or network connection are required.

```bash
python tests/test_facts.py
python tests/test_temporal.py
python harness/run_eval.py --submission submission --eval eval/public_eval.jsonl --out evaluation_results --repeat-sample 10
```

The public evaluator checks 40 questions. The latest **locally tested development implementation** scored **0.7313** with ten repeated-question checks, zero execution errors, and 9.9 seconds for ingestion. That result is not a hidden-set estimate. The source repository is intended to reproduce the implementation; independently rerun the commands above after checkout.

## Temporal and source policy

An `as_of` question selects the latest available snapshot on or before the requested date. Rate-table facts retain both their observed snapshot date and an explicitly stated effective date, where present. An observation date is not automatically an effective date. Rate comparisons preserve product, term, balance tier, and metric (APR versus APY versus dividend rate). Conflicts are reported with competing values, source URLs, and a resolution rationale. Source precedence uses effective-date evidence and authoritative rate sheets; it does not guarantee that every historical disagreement can be resolved.

Answers without sufficient support may abstain. Historical data and the public evaluation are limited; this is not a live banking-rate service.

## Data handling

The website snapshots, extracted website content, and evaluation outputs are **not** committed. Obtain the participant kit from the event organizers. The GitHub Actions workflow runs standalone parser checks without requiring the private kit; the full contract and evaluation commands require the participant kit locally.
