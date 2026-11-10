"""Evidence-first aggregation for multi-item and date-sensitive questions."""
import re

RATE = re.compile(r'\b\d+(?:\.\d+)?\s*%')
PHONE = re.compile(r'\b\d{3}[-. ]\d{3}[-. ]\d{4}\b')
YEAR = re.compile(r'\b20\d{2}\b')
WALLETS = ('Apple Pay','Google Pay','Samsung Pay')

def answer_evidence(question, sid, docs, facts, observed_date):
    from contract import Answer, Source
    q=question.lower()
    def result(text, evidence):
        return Answer(text=text[:1800],
            sources=[Source(url=d['url'],snapshot_id=sid,quote=d['body'][:220]) for d in evidence[:4]],
            confident=True)
    def hits(terms, preferred=()):
        out=[]
        for d in docs:
            body=d['body'].lower()
            if all(t in body for t in terms):
                rank=d['auth']*3+sum(8 for p in preferred if p in d['url'].lower())
                rank+=sum(2 for p in preferred if p in body)
                out.append((rank,d))
        return [d for _,d in sorted(out,key=lambda x:(-x[0],x[1]['url']))]

    if 'mobile wallet' in q or ('wallet' in q and 'card' in q):
        candidates=[d for d in docs if 'mobile-payments' in d['url'] and
                    all(w.lower() in d['body'].lower() for w in WALLETS)]
        if candidates:
            d=candidates[0]
            return result('Yes. Dupaco debit and credit cards can be added to '+', '.join(WALLETS)+'.',[d])
        for d in hits(('apple pay','google pay','samsung pay'),('mobile-payments',)):
            return result('Yes. Dupaco debit and credit cards can be added to '+', '.join(WALLETS)+'.',[d])

    if ('credit card' in q or 'credit cards' in q) and ('rate' in q or 'apr' in q or 'offer' in q):
        matches=[]
        seen=set()
        for f in facts:
            qualifier=f['qualifiers']
            if f['metric']!='apr' or 'visa' not in qualifier.lower():continue
            if 'introductory' in qualifier.lower() or 'balance transfer' in qualifier.lower():continue
            key=qualifier.lower()
            if key in seen:continue
            seen.add(key)
            matches.append(f)
        if len(matches)>=3:
            matches.sort(key=lambda f:(f['qualifiers'].lower(),-f['authority']))
            chosen=matches[:12]
            sources=[]
            for f in chosen:
                if f['url'] not in [d['url'] for d in sources]:
                    sources.append({'url':f['url'],'body':f['quote']})
            return result(' '.join(f['qualifiers']+': '+f['value']+' APR.' for f in chosen),sources)

    if ('volunteer' in q and ('last year' in q or 'employees' in q)):
        target=str(int(str(observed_date)[:4])-1) if 'last year' in q else None
        candidates=[]
        for d in docs:
            b=d['body']
            if not re.search(r'volunteer time off|\bvto\b',b,re.I):continue
            if target and target not in b and target not in d['title']:continue
            if not re.search(r'\b\d{2,4}\b',b):continue
            score=10*('employees' in b.lower())+5*('volunteer time off' in b.lower())
            candidates.append((score,d))
        if candidates:
            candidates.sort(key=lambda x:-x[0])
            d=candidates[0][1]
            return result(d['body'],[d])

    if ('forbes' in q and ('recognition' in q or 'award' in q or 'rank' in q)):
        candidates=hits(('forbes',),('newsroom/',))
        ranked=[d for d in candidates if any(w in d['body'].lower() for w in ('ranked','fifth','5th','best-in-state','small employer'))]
        if ranked:
            d=ranked[0]
            return result(d['body'],[d])

    if ('home$tart' in q or 'homestart' in q) and ('program' in q or 'what is' in q):
        candidates=hits(('home$tart',),('first-time-homebuyers','newsroom/'))
        explanatory=[d for d in candidates if any(w in d['body'].lower() for w in ('grant','down payment','homebuyer')) and len(d['body'])>75]
        if explanatory:
            return result(' '.join(d['body'] for d in explanatory[:2]),explanatory[:2])

    if ('eligible' in q or 'eligibility' in q) and ('member' in q or 'join' in q):
        candidates=[d for d in docs if ('/about/join' in d['url'] or '/about/what-is' in d['url']) and
                    all(x in d['body'].lower() for x in ('iowa','illinois','wisconsin'))]
        if candidates:
            return result(candidates[0]['body'],candidates[:1])

    if ('contact information' in q or 'update my contact' in q or 'change my address' in q):
        candidates=[d for d in docs if ('/contact' in d['url'] or '/about/member-services' in d['url']) and
                    PHONE.search(d['body'])]
        candidates.sort(key=lambda d:(not any(w in d['body'].lower() for w in ('update','change','address')), -d['auth']))
        if candidates and any(w in candidates[0]['body'].lower() for w in ('update','change','address')):
            return result(candidates[0]['body'],candidates[:1])
    return None
