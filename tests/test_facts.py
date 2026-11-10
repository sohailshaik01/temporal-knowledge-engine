"""Dependency-free tests for rate parsing and tier separation."""
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'submission'))
from facts import read_table_facts

def test_rates():
    page = SimpleNamespace(url='https://example.test/rates', title='Savings Rates',
        markdown='''# Rates
| Account Type | Balance Tier | Dividend Rate | Annual Percentage Yield (APY) |
| --- | --- | --- | --- |
| Share Savings | $0-$99 | 0.10% | 0.10% |
| Share Savings | $100-$999 | 0.20% | 0.20% |
Rates are effective as of 06/15/2026.
''')
    import re
    toks = lambda s: re.findall(r'[a-z]+|\d+(?:\.\d+)?',s.lower())
    facts = read_table_facts(page,'test-snapshot','2026-09-28',toks,lambda u,t:3)
    assert len(facts)==4, facts
    assert {f['metric'] for f in facts}=={'apy','dividend rate'}
    assert {f['effective'] for f in facts}=={'2026-06-15'}
    assert len({f['key'] for f in facts})==4

if __name__=='__main__':
    test_rates()
    print('Typed fact tests passed')
