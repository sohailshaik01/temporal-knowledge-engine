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
