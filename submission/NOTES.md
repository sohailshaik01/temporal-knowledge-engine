# Temporal knowledge system

This implementation uses only the Python standard library, requires no API keys and never calls the live website. Each ingested snapshot is independently indexed with page URL, heading, crawl identifier, and passage text. Questions with an `as_of` date select the most recent snapshot not later than that date. Unqualified questions use the latest snapshot.

Retrieval combines inverse-document-frequency weighting, title/heading matching, source-authority heuristics, and qualifiers such as term, model year, and account type. Answers cite the chosen snapshot URL and a supporting excerpt. The system abstains when evidence cannot be retrieved. The conflict extractor compares single percentage claims under matching page URLs and headings over time, favoring the latest authoritative version.

This is an offline baseline, not a guarantee of correctness: structured table interpretation, stronger within-snapshot conflict detection, and answer calibration should be validated against the public scorer before final submission. The website snapshot data is intentionally excluded from any public repository.

## Public evaluation

The candidate-postings index limits retrieval to passages containing query terms, rather than scanning every passage. Source ranking now places greater weight on matching page titles and official product pages, and returns longer evidence when a short excerpt would lose relevant table context.

The latest local run against the 40-question public evaluation scored 0.3722 with repeat checks disabled, compared with 0.1924 for the previous baseline. Snapshot ingestion completed in 4.9 seconds. The score remains below the desired quality threshold, and the implementation is not ready for final grading. No benchmark data or website snapshot content is included in the repository.

## Evidence ranking

The retrieval ranker now favors numeric table rows over rate disclaimers, distinguishes jumbo certificate tiers from standard certificates, and downranks historical educational material for current loan-rate questions. It also rewards explicit numeric qualifiers in the question. These are general ranking rules rather than stored answers to the evaluation questions.

## Evaluation update

The latest local run against the supplied 40-question public evaluation scored 0.4867 overall (previous recorded run: 0.3722), with 4.2 seconds for ingestion and 0.26 seconds at the 95th percentile for answers. This run did not include repeated-question checks. Product category questions now collect evidence across multiple rows, loan and branch questions abstain when specific evidence is missing, and the rate ranker better distinguishes common tiers. Conflict resolution and current-value questions remain weak and require further work. These scores are development diagnostics, not hidden-set results.

## Contact and branch evidence

The latest local public evaluation run (40 questions, repeat checks disabled) scored 0.5177, up from the previous recorded 0.4867. Snapshot ingestion took 4.3 seconds. The retrieval scorer now gives additional weight to passages with explicit telephone numbers for contact queries and clock times for branch-hours queries. The conflict-resolution and current-value categories remain unresolved; this is not a final submission benchmark.

## Structured facts and historical validity

The typed rate extractor stores product and balance/term qualifiers, the financial metric, observed value, source URL, snapshot identifier, and any explicitly published effective date. Queries first attempt qualified fact matching when the requested metric and product are clear, then fall back to the indexed passage retriever. APR, APY, and dividend rate remain distinct. Snapshot selection is ordered by capture date; an effective date is not inferred from a crawl timestamp.

Conflict detection now includes disagreements between matching product/tier/metric facts on different official pages within the latest snapshot, in addition to historical changes. A later explicit effective date has precedence, followed by an official rate sheet and source authority. The system cannot infer a precise validity interval where none was published.

Navigational questions return grounded destination links. Branch-closure questions are answered from the closure notice when it is available in the selected snapshot. The offline runtime uses no external services.

## Latest public evaluation

The latest local development run across all 40 public questions scored **0.7313**, compared with **0.5797** before this iteration. Ten repeat checks were enabled, with 1.0 reported repeat consistency, zero execution errors, and a 9.9-second ingestion time. Category scores included temporal-as-of 0.75, stale-trap 0.59, tier-disambiguation 1.00, and conflict-resolution 0.33. These are public-set diagnostics, not hidden-set performance. The local implementation was tested before the corresponding source modules were committed; a clean-checkout full evaluation remains necessary to verify the committed build independently.

Remaining limitations include incomplete list aggregation, some cross-page conflicts, and questions whose relevant facts are not represented by a structured table.

## Evidence aggregation iteration

The evidence-first module now handles mobile-wallet compatibility, complete credit-card APR rows when present, year-qualified volunteer reporting, Forbes recognition, Home$tart descriptions, membership eligibility, and contact updates. Each specialized answer requires matching passages or typed rate facts from the selected snapshot, retains the supporting source URL, and falls back to the standard retriever when insufficient evidence exists. Standalone synthetic tests cover multi-wallet extraction, unsupported claims, and credit-card APR aggregation.

**Evaluation status:** This change has not yet been measured against the full participant-kit public evaluator. The earlier 0.7313 score must not be interpreted as the score of this revision. Run the public evaluator locally before judging whether the 0.85 development target has been reached.
