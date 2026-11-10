"""Typed financial rate extraction and source provenance."""
import re
from datetime import datetime

RATE_VALUE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s*%")
DATE_VALUE = re.compile(r"(?:effective|accurate) as of\s+(\d{1,2}/\d{1,2}/\d{4})", re.I)

def table_cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]

def normalized_rate(value):
    m = RATE_VALUE.search(value)
    return m.group(0).replace(' ', '') if m else None

def read_table_facts(page, snapshot_id, taken_on, toks, authority):
    facts = []
    header = None
    pending = []
    effective = None
    for line in page.markdown.splitlines() + ['# END']:
        line = line.strip()
        if line.startswith('|'):
            cells = table_cells(line)
            if all(re.fullmatch(r'[-: ]+', c or '-') for c in cells):
                continue
            if any(x in line.lower() for x in ('account type', 'certificate type', 'loan type', 'balance tier', 'dividend rate', 'annual percentage yield', 'interest rate', 'apr', 'term', 'model year')) and not any(RATE_VALUE.search(c) for c in cells):
                if pending:
                    for fact in pending: fact['effective'] = effective
                    facts.extend(pending)
                pending = []
                header = cells
                effective = None
                continue
            if header and len(cells) == len(header) and any(RATE_VALUE.search(c) for c in cells):
                qualifiers = [cells[i] for i,h in enumerate(header) if not RATE_VALUE.search(cells[i]) and not any(w in h.lower() for w in ('minimum','min.'))]
                for i, cell in enumerate(cells):
                    value = normalized_rate(cell)
                    if not value: continue
                    metric = header[i].lower()
                    if 'yield' in metric or 'apy' in metric: metric = 'apy'
                    elif 'apr' in metric: metric = 'apr'
                    elif 'dividend' in metric: metric = 'dividend rate'
                    elif 'interest' in metric: metric = 'interest rate'
                    elif 'rate' in metric: metric = 'rate'
                    else: continue
                    key = (' '.join(toks(' '.join(qualifiers))), metric)
                    pending.append({'key':key,'qualifiers':' | '.join(qualifiers), 'metric':metric, 'value':value,
                                    'url':page.url,'sid':snapshot_id,'taken_on':taken_on,'effective':None,
                                    'quote':line[:280], 'authority':authority(page.url,page.title)})
            continue
        found = DATE_VALUE.search(line)
        if found:
            try: effective = datetime.strptime(found.group(1),'%m/%d/%Y').date().isoformat()
            except ValueError: pass
            if pending:
                for fact in pending: fact['effective'] = effective
                facts.extend(pending)
                pending=[]
            header=None
        elif line.startswith('#'):
            if pending:
                facts.extend(pending)
                pending=[]
            header=None
            effective=None
    return facts

def structured_rate(question, sid, as_of, facts, toks, authority):
    from contract import Answer, Source
    q=question.lower()
    if any(x in q for x in ('what link', 'what url', 'which link', 'link should', 'where can i find')):return None
    if 'checking' in q or 'auto loan' in q or 'vehicle' in q:return None
    if not any(x in q for x in ('apy','apr','interest rate','dividend rate','mortgage rate','certificate rate')):return None
    tokens=set(toks(question))
    products=('mortgage','certificate','auto','personal','checking','saving','visa')
    if not any(x in tokens for x in products):return None
    metric = ('apy' if 'apy' in tokens or 'annual percentage yield' in q else
              'apr' if 'apr' in tokens else 'dividend rate' if 'dividend' in tokens else None)
    number_terms=set(re.findall(r'\b\d{1,4}\b',q))
    jumbo='jumbo' in tokens
    candidates=[]
    for f in facts.get(sid,[]):
        qualifier=f['qualifiers'].lower()
        url=f['url'].lower()
        if 'business' not in tokens and ('business' in qualifier or '/business' in url):continue
        if metric and f['metric']!=metric:continue
        if 'certificate' in tokens and not any(x in qualifier for x in ('certificate','month fixed','month jumbo')):continue
        if 'mortgage' in tokens and not any(x in qualifier for x in ('fixed conventional','mortgage','purchase:')):continue
        if 'auto' in tokens and not any(x in qualifier for x in ('model year','auto')):continue
        if 'checking' in tokens and 'checking' not in qualifier:continue
        if 'saving' in tokens and 'saving' not in qualifier:continue
        if 'visa' in tokens and 'visa' not in qualifier:continue
        if 'jumbo' in qualifier and not jumbo and 'certificate' in tokens:continue
        if jumbo and 'jumbo' not in qualifier:continue
        ft=set(toks(qualifier))
        overlap=len((tokens-{'rate','apr','apy','interest','dividend','month','year'}) & ft)
        score=overlap*4+f['authority']
        if number_terms:
            matched=sum(1 for t in number_terms if re.search(r'(?<!\d)'+re.escape(t)+r'(?!\d)',qualifier))
            score+=matched*13
            if matched==0:score-=18
        if 'mortgage' in tokens and '30' in number_terms and '30-year' in qualifier:score+=8
        if f['effective'] and as_of and f['effective']>str(as_of)[:10]:continue
        if f['url'].rstrip('/')=='https://www.dupaco.com/rates':score+=4
        candidates.append((score,f))
    if not candidates:return None
    candidates.sort(key=lambda z:(-z[0],-z[1]['authority'],z[1]['url']))
    top=candidates[0][0]
    if top<5:return None
    broad='mortgage' in tokens and not number_terms
    if broad:
        chosen=[];seen=set()
        for score,f in candidates:
            if score<top-9:break
            if f['url']!=candidates[0][1]['url']:continue
            if f['key'] in seen:continue
            chosen.append(f);seen.add(f['key'])
            if len(chosen)==8:break
        if len(chosen)>=2:
            return Answer(text=' '.join(f["qualifiers"]+': '+f['metric'].upper()+' '+f['value']+'.' for f in chosen),
                          sources=[Source(url=chosen[0]['url'],snapshot_id=sid,quote=chosen[0]['quote'])],confident=True)
    f=candidates[0][1]
    if number_terms and not any(re.search(r'(?<!\d)'+re.escape(t)+r'(?!\d)',f['qualifiers']) for t in number_terms):return None
    if f['effective'] and f['effective']>f['taken_on']:return None
    return Answer(text=f["qualifiers"]+': '+f['metric'].upper()+' '+f['value']+'.',
                  sources=[Source(url=f['url'],snapshot_id=sid,quote=f['quote'])],confident=True)
