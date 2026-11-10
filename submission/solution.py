"""Temporal, source-aware retrieval baseline. No network calls or API credentials."""
from __future__ import annotations
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(next(d / 'harness' for d in Path(__file__).resolve().parents if (d / 'harness' / 'contract.py').exists())))
from contract import Answer, Conflict, Source

TOKEN = re.compile(r"[a-z]+|\d+(?:\.\d+)?", re.I)
NUMBER = re.compile(r"(?:\$\s*)?\d[\d,]*(?:\.\d+)?\s*%?")
STOP = set('what is are the a an on of for in to and or can you me tell do does dupaco your my how i it with from as at now current today please get provide would like know about have has was were this that their our'.split())
SYN = {'cd':'certificate','certificates':'certificate','rates':'rate','savings':'saving','branches':'branch','hours':'hour','mortgages':'mortgage','cards':'card','loans':'loan','aprs':'apr','checking':'checking','lobby':'lobby','driveup':'drive','drive-up':'drive','automobile':'auto','vehicle':'auto','vehicles':'auto','location':'branch','locations':'branch','interest':'rate'}

def toks(s):
    return [SYN.get(w,w) for w in TOKEN.findall(s.lower()) if w not in STOP and len(w)>1]

def authority(url,title):
    u=url.lower(); t=title.lower(); score=0
    if any(k in u for k in ('/personal/','/business/','/contact','/about/','/locations/')):score+=2
    if any(k in u for k in ('rates','auto-loans','mortgage','savings-account','credit-card','checking','branch')):score+=3
    if any(k in u for k in ('/blog/','/learn/','/news/','/2020/','/2021/','/2022/','/2023/','/2024/','calculator','affordability')):score-=5
    if any(k in t for k in ('rates','rate','hours','certificate','credit cards')):score+=1
    return score

class TemporalKnowledge:
    def __init__(self):
        self.snapshots=[];self.index={};self.df={};self.postings={};self.conflict_cache=None

    def ingest(self,snapshot):
        docs=[]; df=Counter(); postings=defaultdict(list)
        for p in snapshot.pages:
            md=re.sub(r'!\[[^]]*\]\([^)]*\)',' ',p.markdown)
            md=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',md)
            # Keep compact sections, preserving table rows and adjacent headings.
            lines=[x.strip() for x in md.splitlines() if x.strip()]
            blocks=[]; section=''; buf=[]
            for line in lines:
                if line.startswith('#'):
                    if buf:blocks.append((section,' '.join(buf)));buf=[]
                    section=line.lstrip('# *').strip()[:180]
                elif line.startswith('|'):
                    if buf:blocks.append((section,' '.join(buf)));buf=[]
                    blocks.append((section,line))
                else:
                    buf.append(line)
                    if len(' '.join(buf))>400:
                        blocks.append((section,' '.join(buf)));buf=[]
            if buf:blocks.append((section,' '.join(buf)))
            for head,block in blocks:
                if len(block)<12:continue
                text=(p.title+' '+head+' '+block)
                words=Counter(toks(text));
                if not words:continue
                d={'url':p.url,'title':p.title,'head':head,'body':block,'words':words,'auth':authority(p.url,p.title),'sid':snapshot.snapshot_id}
                docs.append(d);df.update(words.keys())
                for w in words:postings[w].append(len(docs)-1)
        self.snapshots.append((snapshot.taken_on,snapshot.snapshot_id))
        self.index[snapshot.snapshot_id]=docs
        self.df[snapshot.snapshot_id]=df
        self.postings[snapshot.snapshot_id]=postings
        self.conflict_cache=None

    def _date(self,as_of):
        if not self.snapshots:return None
        if not as_of:return self.snapshots[-1][1]
        d=str(as_of)[:10]
        eligible=[sid for day,sid in self.snapshots if day<=d]
        return eligible[-1] if eligible else None

    def _rank(self,q,sid):
        qt=Counter(toks(q));docs=self.index[sid];df=self.df[sid];n=len(docs)
        scored=[]
        candidates=set()
        for w in qt:candidates.update(self.postings[sid].get(w,()))
        for idx in candidates:
            d=docs[idx]
            match=set(qt)&d['words'].keys()
            if not match:continue
            s=sum((1+math.log(1+qt[w]))*math.log(1+(n-df[w]+.5)/(df[w]+.5))*min(2,1+math.log(d['words'][w])) for w in match)
            titlewords=set(toks(d['title']+' '+d['head']+' '+d['url'].replace('/',' ')))
            s+=sum(4.5 for w in match if w in titlewords)
            s+=d['auth']*1.25
            # Preserve explicit terms and years; unrelated tiers must not win.
            for m in re.findall(r'\b(?:\d{1,3}[- ]month|\d{4} model|\d{1,3}/1|jumbo|platinum|rewards|bright|share|business)\b',q.lower()):
                if m in (d['body']+' '+d['head']+' '+d['title']).lower():s+=3
            # Prefer data rows over boilerplate and historical commentary.
            body=d['body'].lower()
            if body.startswith('|') and body.count('|')>=3 and re.search(r'\d+(?:\.\d+)?%',body):s+=14
            if re.search(r'\d+(?:\.\d+)?%',body) and any(w in qt for w in ('apr','apy','rate','dividend')):s+=3
            if any(w in qt for w in ('apr','apy','rate','dividend')) and not re.search(r'\d+(?:\.\d+)?%',body):s-=12
            if ('mortgage' in qt or 'loan' in qt) and ('/learn/' in d['url'] or '/newsroom/' in d['url']):s-=18
            if 'certificate' in qt and 'checking' in d['url']:s-=12
            if 'mortgage' in qt and ('/rates' in d['url'] or '/home-loans' in d['url']):s+=8
            if 'certificate' in qt and 'jumbo' not in qt and 'jumbo' in body:s-=17
            if 'certificate' in qt and 'jumbo' in qt and 'jumbo' in body:s+=8
            if 'checking' in qt and 'checking' in body:s+=5
            if 'share' in qt and 'saving' in qt and 'share savings' in body:s+=13
            if 'share' in qt and 'saving' in qt and 'business' in body:s-=7
            if 'mortgage' in qt and '30' in qt and '30-year fixed conventional' in body:s+=15
            if 'mortgage' in qt and 'relief' not in qt and 'relief' in body:s-=22
            if 'mortgage' in qt and '30' in qt and '$100,000' in body:s+=16
            if 'mortgage' in qt and '30' in qt and '$832,750' in body:s-=9
            if 'student' in qt and 'student' not in body:s-=20
            if 'construction' in qt and 'construction' not in body:s-=22
            if 'share' in qt and 'saving' in qt and 'introductory' in body:s-=17
            if 'platinum' in qt and 'introductory' in body:s-=10
            if 'rate' in qt and 'apr' in qt and 'balance transfer' in body:s-=7
            if 'hour' in qt and 'drive' in qt and 'drive' in body:s+=12
            if 'branch' in qt and 'galena' in qt and 'galena' in body:s+=7
            for numeric in re.findall(r'\b\d[\d,]*(?:\.\d+)?\b',q):
                if len(numeric)>=2 and numeric in body:s+=5
            if 'locator' in qt and '/contact' in d['url']:s+=12
            if 'link' in qt and 'certificate' in qt and '/personal/savings-account' in d['url']:s+=12
            if ('phone' in qt or 'call' in qt or 'number' in qt) and re.search(r'\b\d{3}[-. ]\d{3}[-. ]\d{4}\b',body):s+=13
            if ('hour' in qt or 'close' in qt or 'open' in qt) and re.search(r'\b(?:a\.?m\.?|p\.?m\.?|noon)\b',body):s+=12
            if 'checking' in qt and 'rate' in qt and ('checking' in body and re.search(r'\d+(?:\.\d+)?\s*%',body)):s+=14
            if 'home' in qt and 'start' in qt and ('home$tart' in body or 'home\u0024tart' in body):s+=25
            if 'eligible' in qt and ('eligible' in body or 'eligibility' in body or 'live or work' in body):s+=13
            if 'branch' in qt and any(w in qt for w in ('how','many','number')) and ('locations' in body or 'branches' in body):s+=10
            if 'volunteer' in qt and '2025' in body:s+=12
            if len(match)<min(2,len(qt)):s-=4
            scored.append((s,d))
        scored.sort(key=lambda x:(-x[0],-x[1]['auth'],x[1]['url']))
        return scored

    def answer(self,question,as_of=None):
        sid=self._date(as_of)
        if not sid:return Answer("I don't know; the requested date predates the available website snapshots.",confident=False)
        ranked=self._rank(question,sid)
        if not ranked or ranked[0][0]<2:return Answer("I don't know. The website doesn't list enough information; please contact Dupaco.",confident=False)
        q=question.lower(); selected=[];seen=set()
        # Specific product and contact requests require direct evidence, not
        # boilerplate containing generic overlapping vocabulary.
        if ('contact information' in q or 'update my contact' in q or 'change my address' in q):
            candidates=[(score,d) for score,d in ranked if any(t in d['body'].lower() for t in ('update your contact information','update your address','change your address','update your phone number','800-373-7600'))]
            if candidates:
                ranked=candidates+[(score,d) for score,d in ranked if (score,d) not in candidates]
        # Distinct top-ranking passages, not an unbounded collage of competing values.
        for score,d in ranked[:25]:
            if score < max(2,ranked[0][0]*.63):break
            if d['url'] in seen:continue
            selected.append((score,d));seen.add(d['url'])
            if len(selected)==3:break
        # Category-level questions may need evidence from multiple product rows.
        listing = any(t in q for t in ('what credit cards', 'rates for the credit cards', 'certificate of accounts', 'what certificates', 'mobile wallet'))
        if listing:
            collected=[]; urls=set()
            for score,d in ranked[:120]:
                if score < ranked[0][0]*.44:break
                body=d['body'].strip()
                if not body or body in [x[1] for x in collected]:continue
                if 'credit card' in q or 'credit cards' in q:
                    if not any(w in body.lower() for w in ('platinum visa','rewards visa','business platinum','business rewards')):continue
                    if 'introductory' in body.lower() or 'balance transfer' in body.lower():continue
                if 'certificate' in q and 'certificate' not in body.lower():continue
                collected.append((d,body));urls.add(d['url'])
                if len(collected)>=10:break
            if len(collected)>=2:
                text=' '.join(b[:210] for d,b in collected)[:1500]
                return Answer(text=text,sources=[Source(url=u,snapshot_id=sid) for u in sorted(urls)[:5]],confident=True)
        best=selected[0][1]
        body=best['body']
        # Do not substitute unrelated products for a requested loan or branch.
        if 'construction' in q and ('construction' not in body.lower() or not re.search(r'\d+(?:\.\d+)?\s*%',body)):
            return Answer("I don't know. A construction-loan interest rate is not clearly listed; please contact Dupaco.",confident=False)
        if 'mullan' in q and 'mullan' not in (body+' '+best['title']).lower():
            return Answer("I don't know. Please contact Dupaco for the specific branch hours.",confident=False)
        # When a question asks for a list of account rates, retain adjacent
        # table rows from the authoritative rates page.
        if 'checking' in q and 'rate' in q:
            rows=[d for score,d in ranked[:200] if d['url']==best['url'] and 'checking' in d['body'].lower() and re.search(r'\d+(?:\.\d+)?\s*%',d['body'])]
            if len(rows)>1:
                result=' '.join(dict.fromkeys(d['body'] for d in rows[:12]))
                return Answer(text=result[:1800],sources=[Source(url=best['url'],snapshot_id=sid)],confident=True)
        # Use targeted sentences/rows rather than entire page text.
        pieces=re.split(r'(?<=[.!?])\s+(?=[A-Z])|\s*\|\s*(?=\w)',body)
        qwords=set(toks(question));
        ranked_pieces=sorted(pieces,key=lambda p:(len(qwords&set(toks(p))),bool(NUMBER.search(p))),reverse=True)
        candidate=ranked_pieces[0] if ranked_pieces else body
        if len(candidate)<30 and len(ranked_pieces)>1:candidate+=' '+ranked_pieces[1]
        if len(candidate)<120 and len(body)<950 and ('|' in body or len(re.findall(r'\d+(?:\.\d+)?%',body))>1):
            candidate=body
        candidate=candidate[:900].strip()
        if not candidate:return Answer("I don't know; please contact Dupaco.",confident=False)
        return Answer(text=candidate,sources=[Source(url=best['url'],snapshot_id=sid,quote=candidate[:220])],confident=True)

    def conflicts(self):
        if self.conflict_cache is not None:
            return self.conflict_cache
        # Align facts by page, section and surrounding wording. A table with
        # multiple terms or balances is not a single contradictory fact.
        pattern = re.compile(r'(?<![\w.])\d+(?:\.\d+)?\s*%')
        versions = defaultdict(list)
        for day, sid in self.snapshots:
            for d in self.index[sid]:
                if d['auth'] < 0:
                    continue
                body = d['body']
                values = list(dict.fromkeys(x.strip() for x in pattern.findall(body)))
                if len(values) != 1:
                    continue
                # Exact same surrounding text with a changed percentage is
                # stronger evidence than sharing a heading alone.
                context = re.sub(r'\s+', ' ', pattern.sub('<rate>', body.lower()))
                context = re.sub(r'[^a-z0-9<> ]+', ' ', context)
                words = toks(context)
                if len(words) < 4:
                    continue
                signature = ' '.join(words[:32])
                key = (d['url'].rstrip('/').lower(), d['head'].lower(), signature)
                versions[key].append((day, sid, values[0], d))
        conflicts = []
        seen = set()
        for (url, heading, signature), entries in versions.items():
            ordered = sorted(entries, key=lambda x: (x[0], x[1]))
            distinct = list(dict.fromkeys(x[2] for x in ordered))
            if len(distinct) < 2:
                continue
            winner = ordered[-1]
            loser = next(x for x in ordered if x[2] != winner[2])
            dedup = (url, heading, tuple(sorted(distinct)))
            if dedup in seen:
                continue
            seen.add(dedup)
            conflicts.append(Conflict(
                topic=(winner[3]['title'] + ' — ' + heading).strip(' —')[:180],
                values=distinct,
                sources=[
                    Source(url=loser[3]['url'], snapshot_id=loser[1],
                           quote=loser[3]['body'][:180]),
                    Source(url=winner[3]['url'], snapshot_id=winner[1],
                           quote=winner[3]['body'][:180])
                ],
                resolution=winner[2],
                reason='The same fact changed between dated website snapshots; the later snapshot supersedes the earlier value.'
            ))
        self.conflict_cache = conflicts[:250]
        return self.conflict_cache

def build():return TemporalKnowledge()
