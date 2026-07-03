# -*- coding: utf-8 -*-
"""READ-ONLY: reconcile raw Customer (Account QLF + QLI) vs Jayson Counterparty v2 (Is Customer).
Find which customers are 'missing' (raw 307 vs jayson 305). No writes."""
import re, glob, time
import pandas as pd, openpyxl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def gcol(df,name):
    for c in df.columns:
        if str(c).strip().lower()==name.lower(): return c
    return None
def val(x):
    x=str(x).strip(); return '' if x.lower()=='nan' else x

# ---- RAW customers ----
def read_cust(pat, side):
    f=[x for x in glob.glob(f'{D}/*.xlsx') if pat in x][0]
    # header row detection: try 0 then 1
    for hdr in (0,1):
        df=pd.read_excel(f, sheet_name='Customer', header=hdr, dtype=str).fillna('')
        if gcol(df,'M3 Code') is not None: break
    mc=gcol(df,'M3 Code'); nm=gcol(df,'name') or gcol(df,'Name')
    out=[]
    for _,r in df.iterrows():
        code=val(r[mc]) if mc is not None else ''
        name=val(r[nm]) if nm is not None else ''
        if not code and not name: continue
        out.append({'code':code,'name':name,'side':side})
    return out, list(df.columns)

qlf,qlf_cols=read_cust('Account QL Feed','QLF')
qli,qli_cols=read_cust('Account QL International -','QLI')
print('QLF Customer cols:',qlf_cols)
print('raw QLF rows(non-empty):',len(qlf),' QLI rows:',len(qli))

# drop rows with no M3 code (banners/blanks)
qlf_c=[r for r in qlf if r['code']]
qli_c=[r for r in qli if r['code']]
print('QLF with M3 code:',len(qlf_c),' QLI with M3 code:',len(qli_c),' total:',len(qlf_c)+len(qli_c))
raw=qlf_c+qli_c
raw_codes={}
for r in raw: raw_codes.setdefault(r['code'],[]).append(r)
print('raw distinct customer M3 codes:',len(raw_codes))

# ---- Jayson Counterparty v2 ----
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
h=[c.strip() for c in v[0]]
def idx(n):
    for i,c in enumerate(h):
        if c.lower()==n.lower(): return i
    return -1
i_mc=idx('M3 Code'); i_ic=idx('Is Customer'); i_nm=idx('name'); i_vc=idx('M3 Vendor Code (for merged vendor & customer)')
jay=[]
for r in v[1:]:
    r=r+['']*(len(h)-len(r))
    jay.append({'code':r[i_mc].strip(),'is_cust':r[i_ic].strip().upper(),'name':r[i_nm].strip(),
                'vcode':(r[i_vc].strip() if i_vc>=0 else '')})
cust_rows=[j for j in jay if j['is_cust'] in ('TRUE','T','1','YES')]
print('\nJayson Is Customer=TRUE rows:',len(cust_rows))
jay_cust_codes=set(j['code'] for j in cust_rows if j['code'])
print('Jayson customer distinct M3 codes:',len(jay_cust_codes))

# ---- diff ----
# a raw customer code is "covered" if it appears as M3 Code on any Is-Customer row
missing=[c for c in raw_codes if c not in jay_cust_codes]
print('\n=== RAW customer codes NOT flagged Is Customer in Jayson ===')
for c in sorted(missing):
    for r in raw_codes[c]:
        # where does this code exist in jayson at all?
        hits=[j for j in jay if j['code']==c]
        loc=' | '.join(f"{j['name']}[isCust={j['is_cust'] or '-'}]" for j in hits) or 'NOT IN CPv2 AT ALL'
        print(f"  {c} ({r['side']}) raw='{r['name']}'  jayson: {loc}")
print(f"\nTOTAL missing raw customer codes: {len(missing)}")
