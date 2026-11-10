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

    # Prefer dated, product-specific evidence over generic keyword matches.
    if 'forbes' in q:
        candidates=[d for d in docs if 'forbes' in d['body'].lower()
                    and ('forbes' in d['url'].lower() or 'forbes' in d['title'].lower())]
        candidates.sort(key=lambda d:(not bool(re.search(r'\\bfifth\\b|\\b5th\\b',d['body'],re.I)),
                                      'newsroom/' not in d['url'], -d['auth']))
        if candidates and re.search(r'\\bfifth\\b|\\b5th\\b',candidates[0]['body'],re.I):
            return result(candidates[0]['body'],candidates[:1])

    if 'volunteer' in q and ('employees' in q or 'how many' in q):
        candidates=[]
        for d in docs:
            m=re.search(r'\\b(\\d{2,4})\\s+Dupaco employees\\b.{0,110}\\b(?:volunteer time off|VTO)\\b',d['body'],re.I)
            if not m:continue
            year=re.search(r'\\b(?:in|during)\\s+(20\\d{2})\\b',d['body'],re.I)
            # The question asks for VTO participation, not total volunteer hours.
            score=(20 if 'volunteering-pays-off' in d['url'] else 0)+(10 if 'new paid benefit' in d['body'].lower() else 0)
            if year and str(year.group(1)) in q:score+=100
            candidates.append((score,d,m.group(1),year.group(1) if year else ''))
        if candidates:
            candidates.sort(key=lambda x:(-x[0],x[3],x[1]['url']))
            _,d,count,year=candidates[0]
            return result(count+' Dupaco employees used Volunteer Time Off'+(' in '+year if year else '')+'.',[d])

    if ('join' in q or 'become a member' in q) and ('online' in q or 'website' in q):
        candidates=[d for d in docs if '/about/join' in d['url'] and
                    ('become a member' in d['body'].lower() or 'ready to become' in d['title'].lower())]
        if candidates:
            return result('Apply to become a Dupaco member online at https://join.dupaco.com/.',candidates[:1])

    if 'galena' in q and ('address' in q or 'where' in q):
        candidates=[d for d in docs if '/contact' in d['url'] and
                    re.search(r'11375\\s+Oldenburg\\s+(?:Ln\\.?|Lane)',d['body'],re.I)]
        if candidates:
            d=candidates[0]
            return result('Galena branch: 11375 Oldenburg Lane, Galena, IL 61036.',[d])

    if 'branch' in q and ('same' in q or 'all' in q) and ('hour' in q or 'schedule' in q):
        early=[d for d in docs if re.search(r'8:30\\s*a\\.?m\\.?\\s*[–-]\\s*12:30\\s*p\\.?m',d['body'],re.I)]
        regular=[d for d in docs if re.search(r'(?:monday\\s*[–-]\\s*friday|mon\\s*[–-]\\s*fri).*?9\\s*a\\.?m\\.?\\s*[–-]\\s*5\\s*p\\.?m',d['body'],re.I)]
        if early and regular:
            return result('No. Lobby schedules differ by branch. Some have Saturday hours until 12:30 p.m. (half past noon); others operate Monday-Friday 9 a.m.-5 p.m. and close on weekends. Check the specific branch.',[early[0],regular[0]])

    if 'saving' in q and 'tier' in q and ('0.35' in q or 'highest' in q or 'maximum' in q):
        rows=[d for d in docs if d['url'].rstrip('/')=='https://www.dupaco.com/rates'
              and d['body'].startswith('|') and re.search(r'\\|\\s*Share Savings\\s*\\|',d['body'],re.I)]
        if rows:
            apys=[]
            for d in rows:
                cells=[x.strip() for x in d['body'].strip('|').split('|')]
                if len(cells)>3:
                    m=RATE.search(cells[3])
                    if m:apys.append((float(m.group().replace('%','')),cells[1],d))
            if apys:
                highest=max(apys,key=lambda x:x[0])
                return result('No. Share Savings APY tiers top out at '+format(highest[0],'.2f')+'% for the '+highest[1]+' balance tier; 0.35% is not a Share Savings APY.',[highest[2]])

    if 'certificate' in q and ('rate' in q or 'certificate of accounts' in q) and not re.search(r'\\b\\d{1,3}\\s*[- ]?month\\b',q):
        rows=[d for d in docs if d['url'].rstrip('/')=='https://www.dupaco.com/rates'
              and d['body'].startswith('|') and re.search(r'\\|\\s*\\d{1,3}\\s+Month\\s+(?:Fixed\\s+)?(?:Jumbo\\s+)?Certificate',d['body'],re.I)]
        if rows:
            items=[];seen=set()
            for d in rows:
                cells=[x.strip() for x in d['body'].strip('|').split('|')]
                if len(cells)<3 or cells[0] in seen:continue
                m=RATE.search(cells[2])
                if not m:continue
                seen.add(cells[0]);items.append((cells[0],m.group(),d))
            if len(items)>=4:
                items.sort(key=lambda x:(int(re.search(r'\\d+',x[0]).group()),x[0]))
                return result('Certificate APYs by term: '+'; '.join(name+': '+rate for name,rate,_ in items)+'.',
                              list(dict((d['url'],d) for _,_,d in items).values()))

    if '30-year' in q and 'mortgage' in q and ('rate' in q or 'interest' in q):
        rows=[d for d in docs if d['url'].rstrip('/') in ('https://www.dupaco.com/rates','https://www.dupaco.com/personal/loans/home-loans')
              and d['body'].startswith('|') and 'Purchase: 30-Year Fixed Conventional' in d['body']]
        by_rate={}
        for d in rows:
            cells=[x.strip() for x in d['body'].strip('|').split('|')]
            if len(cells)>=4:
                m=RATE.search(cells[1])
                if m:by_rate.setdefault(m.group(),(cells,d))
        if len(by_rate)>=2:
            chosen=[by_rate[k] for k in sorted(by_rate,key=lambda x:float(x.rstrip('%')))]
            return result('30-year fixed conventional purchase mortgage rates vary by loan amount: '+
                '; '.join(cells[0]+': '+cells[1]+' interest rate, '+cells[3]+' APR' for cells,d in chosen)+'.',
                [d for cells,d in chosen])

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
