# Implementation notes

## Scope

The system answers questions against a finite series of dated website snapshots. It does not crawl the live site, use external APIs, or require API keys. The runtime uses Python's standard library and implements the participant harness contract through `build()`, `ingest()`, `answer()`, and `conflicts()`.

## Snapshot model and temporal semantics

Each snapshot is ingested into its own passage index and typed-fact collection. Indexed passages retain page URL, title, heading, body, and snapshot ID. The engine selects the most recent captured snapshot not later than an `as_of` date, or the latest available snapshot when no date is specified. Questions predating the first snapshot return an unconfident answer.

The rate extractor records an explicit published effective date when available, separately from the snapshot capture date. A crawl date is **not** treated as a published effective date. When comparing facts, APR, APY, dividend rate, product, and term/balance qualifiers are kept distinct.

## Retrieval and answers

A postings index limits candidate passages to those containing query terms. Candidate ranking combines inverse-document-frequency weighting, matches in titles and headings, source-authority heuristics, and numeric/product qualifiers. Relevant rate rows are preferred over general disclosures; unrelated products, historical educational pages, and ambiguous tiers are downranked.

The answer path uses evidence aggregation and typed-rate matching when applicable, followed by ranked passage retrieval. Specific evidence rules cover cases such as multi-row certificate and card rates, mobile wallets, branch information, membership links, and dated announcements. These rules rely on ingested content rather than live lookups. Answers include snapshot-specific source references and, where available, excerpts. The engine abstains when it cannot substantiate a requested fact.

## Conflict detection and resolution

The `conflicts()` method reports disagreements using three complementary paths:

1. **Historical single-rate passages:** Compare passages with one percentage under matching URL, heading, and normalized surrounding text.
2. **Qualified certificate rates:** Compare APY/APR values for the same month-term certificate at the same URL across dated snapshots, even when several certificate terms appear in one passage. Unchanged terms are not reported as conflicts.
3. **Within-snapshot typed facts:** Compare matching product/tier/metric keys across authoritative pages in the latest snapshot.

Historical conflicts favor the latest captured version. For disagreements across official pages in one snapshot, explicit effective dates take precedence, followed by recognized rate-sheet authority and source-authority heuristics. Each reported conflict includes values, supporting source references, a resolution, and a reason.

These are evidence-based heuristics, not a general semantic contradiction detector. Changed URLs or differently worded claims may evade alignment; sparse or conflicting effective-date metadata can limit certainty. Multi-rate historical passages outside the specifically qualified certificate pattern are not comprehensively aligned.

## Validation

The following results were observed locally with the participant kit after the certificate conflict fix at commit `b1f70a2677391fd099459f8b1d5e391639abdb5b`:

| Evaluation | Observed result |
| --- | --- |
| Public QA evaluation | 0.955 over 40 questions |
| Repeat consistency | 1.0 over 10 checks |
| Paraphrase consistency | 1.0 over 20 groups |
| Public errors | 0 |
| Public p95 answer latency | 0.06 s |
| Public ingestion | 1.5 s |
| Supplied conflict self-test | F1 1.0; 1 expected, 1 submitted, 1 matched |
| Conflict resolution on self-test | 1.0 |

The supplied conflict self-test has only one gold conflict, a 6-month certificate APY change from 2.95% to 3.50%. The unchanged 12-month rate should not trigger a conflict. The contract-level synthetic tests passed after the fix.

The public QA run did not supply conflict gold, so it does not measure the conflict pillar. Conversely, the separate conflict self-test's QA score was 0.6. Results should be read as targeted checks, not a prediction of hidden evaluation.

## Known limitations

- Retrieval and extraction rules are tailored to common website and financial-rate formats; unseen phrasing and layout changes may reduce accuracy.
- List completeness remains imperfect (0.75 on the public list-completeness category).
- Historical conflict matching is conservative to limit false positives; it may miss cross-page or multi-value contradictions.
- The evaluator's free-text cases may not be fully reflected by deterministic public checks.
- Source precedence cannot establish an exact validity interval when a page does not publish one.
- The system is offline and cannot verify whether a website fact remains true beyond the latest supplied snapshot.

## Reproducibility and data boundaries

Run standalone checks with `python3.11 tests/test_facts.py` and `python3.11 tests/test_evidence.py`. Contract tests and the full public evaluator require the separately supplied participant kit. The public repository contains implementation code and synthetic regression tests, but not website snapshots, private evaluation files, generated reports, or credentials.
