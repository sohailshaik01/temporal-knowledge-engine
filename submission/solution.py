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
        self.snapshots=[];self.index={};self.df={};self.conflict_cache=None

    def ingest(self,snapshot):
        docs=[]; df=Counter()
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
        self.snapshots.append((snapshot.taken_on,snapshot.snapshot_id))
        self.index[snapshot.snapshot_id]=docs
        self.df[snapshot.snapshot_id]=df
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
        for d in docs:
            match=set(qt)&d['words'].keys()
            if not match:continue
            s=sum((1+math.log(1+qt[w]))*math.log(1+(n-df[w]+.5)/(df[w]+.5))*min(2,1+math.log(d['words'][w])) for w in match)
            titlewords=set(toks(d['title']+' '+d['head']+' '+d['url'].replace('/',' ')))
            s+=sum(1.9 for w in match if w in titlewords)
            s+=min(3,d['auth']*.48)
            # Preserve explicit terms and years; unrelated tiers must not win.
            for m in re.findall(r'\b(?:\d{1,3}[- ]month|\d{4} model|\d{1,3}/1|jumbo|platinum|rewards|bright|share|business)\b',q.lower()):
                if m in (d['body']+' '+d['head']+' '+d['title']).lower():s+=3
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
        # Distinct top-ranking passages, not an unbounded collage of competing values.
        for score,d in ranked[:25]:
            if score < max(2,ranked[0][0]*.63):break
            if d['url'] in seen:continue
            selected.append((score,d));seen.add(d['url'])
            if len(selected)==3:break
        best=selected[0][1]
        body=best['body']
        # Use targeted sentences/rows rather than entire page text.
        pieces=re.split(r'(?<=[.!?])\s+(?=[A-Z])|\s*\|\s*(?=\w)',body)
        qwords=set(toks(question));
        ranked_pieces=sorted(pieces,key=lambda p:(len(qwords&set(toks(p))),bool(NUMBER.search(p))),reverse=True)
        candidate=ranked_pieces[0] if ranked_pieces else body
        if len(candidate)<30 and len(ranked_pieces)>1:candidate+=' '+ranked_pieces[1]
        candidate=candidate[:430].strip()
        if not candidate:return Answer("I don't know; please contact Dupaco.",confident=False)
        return Answer(text=candidate,sources=[Source(url=best['url'],snapshot_id=sid,quote=candidate[:220])],confident=True)

    def conflicts(self):
        if self.conflict_cache is not None:return self.conflict_cache
        # Compare numeric claims only across the same URL/heading, rather than
        # treating different tiers or unrelated figures as contradictions.
        versions=defaultdict(list)
        for day,sid in self.snapshots:
            for d in self.index[sid]:
                if d['auth']<0:continue
                vals=tuple(sorted(set(re.findall(r'\b\d+(?:\.\d+)?\s*%',d['body']))))
                if len(vals)==1:
                    versions[(d['url'],d['head'].lower())].append((day,sid,vals[0],d))
        out=[]
        for (url,head),items in versions.items():
            vals=list(dict.fromkeys(x[2] for x in items))
            if len(vals)<2:continue
            newest=max(items,key=lambda x:x[0]); oldest=min(items,key=lambda x:x[0])
            out.append(Conflict(topic=(newest[3]['title']+' '+head)[:180],values=vals[:8],sources=[Source(url=url,snapshot_id=oldest[1]),Source(url=url,snapshot_id=newest[1])],resolution=newest[2],reason='Later snapshot of the same authoritative page and section supersedes earlier rate.'))
        self.conflict_cache=out[:250]
        return self.conflict_cache

def build():return TemporalKnowledge()
