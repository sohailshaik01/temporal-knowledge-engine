"""Contract-level checks using synthetic, non-event data."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "submission"))

from contract import Page, Snapshot
from solution import build


def test_temporal_rate_change():
    ks = build()
    url = "https://example.test/personal/rates"
    for sid, date, rate in [
        ("01_2026-05-12", "2026-05-12", "3.90%"),
        ("02_2026-09-28", "2026-09-28", "4.00%"),
    ]:
        page = Page(
            url=url,
            title="Certificate Rates",
            markdown=f"# Certificate special\nThe special certificate annual percentage yield is {rate} for qualifying deposits.",
            fetched_at=date,
        )
        ks.ingest(Snapshot(snapshot_id=sid, taken_on=date, pages=[page]))
    changes = ks.conflicts()
    assert any(c.resolution == "4.00%" and "3.90%" in c.values for c in changes), changes
    assert ks._date("2026-05-20") == "01_2026-05-12"
    assert ks._date(None) == "02_2026-09-28"


def test_typed_tiers_and_effective_dates():
    ks = build()
    markdown = """# Savings Rates
| Account Type | Balance Tier | Dividend Rate | Annual Percentage Yield (APY) |
| --- | --- | --- | --- |
| Share Savings | $0-$99 | 0.10% | 0.10% |
| Share Savings | $100-$999 | 0.20% | 0.20% |
Rates are effective as of 06/15/2026 and are subject to change.
"""
    ks.ingest(Snapshot("01_2026-09-28", "2026-09-28", [
        Page("https://example.test/rates", "Rates", markdown, "2026-09-28")]))
    facts = ks.facts["01_2026-09-28"]
    assert len(facts) == 4, facts
    assert {f["metric"] for f in facts} == {"apy", "dividend rate"}
    assert {f["effective"] for f in facts} == {"2026-06-15"}
    assert not ks.conflicts(), "Distinct balance tiers must not be treated as contradictions"


def test_missing_history():
    ks = build()
    ks.ingest(Snapshot("01_2026-09-28", "2026-09-28", [
        Page("https://example.test/rates", "Rates", "# Rates\nSome account information.", "2026-09-28")]))
    assert not ks.answer("What was the rate?", as_of="2026-01-01").confident


if __name__ == "__main__":
    test_temporal_rate_change()
    test_typed_tiers_and_effective_dates()
    test_missing_history()
    print("Synthetic temporal checks passed")
