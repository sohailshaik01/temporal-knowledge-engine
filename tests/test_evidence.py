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

if __name__=='__main__':
    test_mobile_wallets()
    test_no_unsubstantiated_wallets()
    test_credit_card_aprs()
    print('Evidence tests passed')
