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


if __name__ == "__main__":
    test_temporal_rate_change()
    print("Synthetic temporal checks passed")
