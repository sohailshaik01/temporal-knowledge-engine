"""Standalone evidence extraction checks, without participant-kit data."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'submission'))
contract=ModuleType('contract')
contract.Source=lambda **kwargs:SimpleNamespace(**kwargs)
contract.Answer=lambda **kwargs:SimpleNamespace(**kwargs)
sys.modules['contract']=contract
from evidence import answer_evidence

def doc(url,body,auth=4):
    return {'url':url,'body':body,'auth':auth,'title':'Page'}

def test_mobile_wallets():
    docs=[doc('https://example.test/mobile-payments',
              'Add your Dupaco debit and credit cards to Apple Pay, Google Pay or Samsung Pay.')]
    answer=answer_evidence('Can I add my debit and credit cards to a mobile wallet?',
        's1',docs,[],'2026-09-28')
    assert answer and all(w in answer.text for w in ('Apple Pay','Google Pay','Samsung Pay'))
    assert answer.sources[0].url==docs[0]['url']

def test_no_unsubstantiated_wallets():
    docs=[doc('https://example.test/marketing','Pay easily with your mobile phone.')]
    assert answer_evidence('Can I use a mobile wallet?', 's1',docs,[],'2026-09-28') is None

def test_credit_card_aprs():
    facts=[{'qualifiers':n+' Visa','metric':'apr','value':v,
            'url':'https://example.test/rates','quote':n+' '+v,'authority':4}
           for n,v in [('Platinum','12.5%'),('Rewards','14.5%'),('Business Platinum','15.5%')]]
    a=answer_evidence('What credit cards do you offer and what are their APRs?',
        's1',[],facts,'2026-09-28')
    assert a and all(f['value'] in a.text for f in facts)


def test_forbes_fifth_recognition():
    docs=[doc('https://example.test/newsroom/forbes-ranks-dupaco',
              'Forbes again named Dupaco a top-rated credit union. This was the fifth time Forbes recognized Dupaco.')]
    a=answer_evidence('What recognition has Dupaco received from Forbes?', 's1',docs,[],'2026-09-28')
    assert a and 'fifth' in a.text

def test_vto_participation_not_total_hours():
    docs=[doc('https://example.test/newsroom/volunteering-pays-off',
              '294 Dupaco employees used a new paid benefit in 2023 called Volunteer Time Off.'),
          doc('https://example.test/hubfs/impact-report.pdf',
              'In 2025, 627 employees volunteered 6,136 hours using Volunteer Time Off.')]
    a=answer_evidence('How many Dupaco employees used Volunteer Time Off last year?', 's1',docs,[],'2026-09-28')
    assert a and '294' in a.text

def test_online_membership():
    docs=[doc('https://www.dupaco.com/about/join','Become a member of Dupaco today.')]
    a=answer_evidence('How do I join Dupaco online?', 's1',docs,[],'2026-09-28')
    assert a and 'https://join.dupaco.com/' in a.text

def test_galena_address():
    docs=[doc('https://www.dupaco.com/contact','11375 Oldenburg Ln., Galena, IL, 61036')]
    a=answer_evidence('What is the address of the Galena Branch?', 's1',docs,[],'2026-09-28')
    assert a and '11375 Oldenburg Lane' in a.text

def test_savings_tier_limit():
    docs=[doc('https://www.dupaco.com/rates','| Share Savings | $25,000+ | 0.20% | 0.20%1 |'),
          doc('https://www.dupaco.com/rates','| Share Savings | $0 – $99.99 | 0.00% | 0.00%1 |')]
    a=answer_evidence('Do any Dupaco savings tiers pay 0.35% APY?', 's1',docs,[],'2026-09-28')
    assert a and '0.20%' in a.text and 'No.' in a.text

def test_certificate_full_list():
    docs=[doc('https://www.dupaco.com/rates',row) for row in (
        '| 17 Month Fixed Jumbo Certificate Special | 4.15% | 4.20%1 |',
        '| 17 Month Fixed Certificate Special | 4.06% | 4.10%2 |',
        '| 60 Month | 1.79% | 1.80%1 |',
        '| 6 Month | 3.37% | 3.40%1 |')]
    a=answer_evidence('Get me the rate for the certificate of accounts.', 's1',docs,[],'2026-09-28')
    assert a and all(x in a.text for x in ('4.20%','4.10%','1.80%','3.40%'))

def test_mortgage_rate_range():
    docs=[doc('https://www.dupaco.com/rates',row) for row in (
        '| Purchase: 30-Year Fixed Conventional $832,750 or less | 7.25% | 0 | 7.29% |',
        '| Purchase: 30-Year Fixed Conventional $100,000 or less | 7.13% | 0 | 7.27% |')]
    a=answer_evidence('Can you tell me the interest rate for a 30-year mortgage?', 's1',docs,[],'2026-09-28')
    assert a and '7.25%' in a.text and '7.13%' in a.text

def test_different_branch_hours():
    docs=[doc('https://example.test/newsroom/branch-a','Saturday: 8:30 a.m.–12:30 p.m.'),
          doc('https://example.test/newsroom/branch-b','Monday-Friday: 9 a.m.–5 p.m.')]
    a=answer_evidence('Do all Dupaco branches keep the same lobby hours?', 's1',docs,[],'2026-09-28')
    assert a and '12:30' in a.text and 'noon' in a.text

if __name__=='__main__':
    test_mobile_wallets()
    test_no_unsubstantiated_wallets()
    test_credit_card_aprs()
    test_forbes_fifth_recognition()
    test_vto_participation_not_total_hours()
    test_online_membership()
    test_galena_address()
    test_savings_tier_limit()
    test_certificate_full_list()
    test_mortgage_rate_range()
    test_different_branch_hours()
    print('Evidence tests passed')
