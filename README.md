# Temporal Knowledge Engine

An offline, source-grounded knowledge system for dated website snapshots. It answers current and historical questions, tracks changes in published facts, reports conflicts with evidence, and abstains when the available material does not support an answer.

The implementation follows the participant kit's `build()`, `ingest(Snapshot)`, `answer(question, as_of=None)`, and `conflicts()` contract. It uses Python 3.11+ and the standard library only. It does not fetch the live website or require API credentials.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `submission/solution.py` | Snapshot indexing, retrieval, time selection, answer construction, and conflict reporting |
| `submission/facts.py` | Typed rate-table extraction, qualifiers, metric separation, and effective-date metadata |
| `submission/evidence.py` | Evidence aggregation and source-grounded answers for multi-part questions |
| `submission/requirements.txt` | Runtime dependency declaration (standard library only) |
| `submission/NOTES.md` | Design decisions, conflict policy, evaluation, and limitations |
| `tests/test_facts.py` | Synthetic structured-fact tests |
| `tests/test_evidence.py` | Synthetic evidence retrieval and aggregation tests |
| `tests/test_temporal.py` | Contract-level temporal and conflict tests; requires the participant harness |

## How it works

1. **Ingest:** Each dated snapshot is indexed separately. Passages retain their source URL, page title, section heading, and snapshot identifier. A token-postings index narrows retrieval candidates.
2. **Select time:** An `as_of` question uses the latest captured snapshot on or before the requested date; a question without `as_of` uses the latest snapshot. If the requested date predates the available history, the engine abstains.
3. **Retrieve evidence:** The engine combines term weighting, title and heading matches, source-authority signals, and product-specific qualifiers. Structured financial tables preserve product, term, balance tier, and metric distinctions such as APR versus APY.
4. **Answer with provenance:** Evidence-backed answers include source URLs and snapshot identifiers, with excerpts where available. Some multi-item questions aggregate evidence from several rows or passages. Unsupported questions may receive an unconfident answer rather than a guessed value.
5. **Report conflicts:** The detector compares matching single-rate passages across snapshots, qualified certificate terms, and conflicting typed facts across authoritative pages in the latest snapshot. Each reported conflict includes competing values, sources, a chosen resolution, and a rationale.

## Run locally

The supplied participant kit is **not** included in this repository. Obtain it from the assignment organizers. A typical local layout is:

```text
hackathon-knowledge-kit-participant/
  harness/
  eval/
  snapshots_zip/            # supplied privately
  submission/               # copy from this repository
  tests/                    # copy from this repository
```

From a checkout of this repository, run the standalone checks:

```bash
python3.11 tests/test_facts.py
python3.11 tests/test_evidence.py
```

To run the contract tests and public evaluator, copy the `submission/` directory and `tests/test_temporal.py` into the participant kit, then run from its root:

```bash
PYTHONPATH="$PWD/harness:$PWD/submission" python3.11 tests/test_temporal.py

python3.11 harness/run_eval.py \
  --submission submission \
  --eval eval/public_eval.jsonl \
  --out evaluation_results \
  --repeat-sample 10
```

To run the participant kit's small conflict self-test:

```bash
python3.11 harness/run_eval.py \
  --submission submission \
  --snapshots harness/selftest/snapshots \
  --eval harness/selftest/eval.jsonl \
  --conflicts-gold harness/selftest/conflicts_gold.json \
  --out conflict_audit \
  --repeat-sample 5
```

The repository's GitHub Actions workflow runs syntax checks and standalone regression tests. The full evaluator needs the privately supplied participant kit.

## Verified local results

The following results were reported from the participant kit using the source version at commit `b1f70a2677391fd099459f8b1d5e391639abdb5b`:

| Check | Result |
| --- | --- |
| Public question answering | **0.955** across 40 questions |
| Public paraphrase consistency | **1.0** across 20 groups |
| Public repeat consistency | **1.0** across 10 checks |
| Public execution errors | **0** |
| Public ingestion time | **1.5 seconds** |
| Public answer latency (p95) | **0.06 seconds** |
| Supplied conflict self-test | **1.0 F1**, 1 of 1 conflicts matched |
| Conflict resolution accuracy on self-test | **1.0** |

The public 40-question run did **not** include a conflict gold file; the conflict score above comes from a separate, one-conflict synthetic test. These numbers describe local public tests, not hidden-set performance. The small self-test's question-answering score was 0.6, so the conflict F1 should not be interpreted as a perfect overall score.

## Limitations and tradeoffs

- The system uses deterministic retrieval and targeted extraction rather than a generative model. This keeps execution offline, fast, and reproducible but limits interpretation of loosely phrased or unfamiliar claims.
- Not all facts are represented as structured rows; some historical or cross-page disagreements can be missed. The certificate-term conflict rule is deliberately narrow to avoid confusing different terms.
- Snapshot capture time and a page's explicitly published effective date are distinct. Where no effective date is stated, the system does not invent one.
- List aggregation and ambiguous source attribution remain areas for improvement. The public evaluation's list-completeness category scored 0.75.
- The system is a historical snapshot analyzer, not a live source of current financial rates.

## Data and security

No supplied website snapshots, private evaluation material, credentials, or generated evaluator reports are included in the public repository. Run the full evaluation locally with the participant kit. See `submission/NOTES.md` for additional implementation details.
