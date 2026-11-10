# Temporal knowledge system

This implementation uses only the Python standard library, requires no API keys and never calls the live website. Each ingested snapshot is independently indexed with page URL, heading, crawl identifier, and passage text. Questions with an `as_of` date select the most recent snapshot not later than that date. Unqualified questions use the latest snapshot.

Retrieval combines inverse-document-frequency weighting, title/heading matching, source-authority heuristics, and qualifiers such as term, model year, and account type. Answers cite the chosen snapshot URL and a supporting excerpt. The system abstains when evidence cannot be retrieved. The conflict extractor compares single percentage claims under matching page URLs and headings over time, favoring the latest authoritative version.

This is an offline baseline, not a guarantee of correctness: structured table interpretation, stronger within-snapshot conflict detection, and answer calibration should be validated against the public scorer before final submission. The website snapshot data is intentionally excluded from any public repository.
