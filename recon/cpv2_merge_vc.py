# -*- coding: utf-8 -*-
"""Minimize CPv2 dups (sheet-only, tunnel down): merge same-(LE,name) Vendor+Customer pairs into ONE row
(Is Vendor+Is Customer, M3 Vendor Code=vendor code) per user design; drop exact same-code/same-side dups.
Leave same-name/different-code pairs (documented). Backup + audit."""
import re, csv, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
h=[c.strip() for c in v[0]]
I={x:h.index(x) for x in ['M3 Code','Vendor / Customer','Is Vendor','Is Customer','M3 Vendor Code (for merged vendor & customer)','name','legal_entity_id','M3 code + Vendor / Customer']}
with open(f"{BK}/Counterparty v2.pre-vcmerge.csv",'w',newline='') as f: csv.writer(f).writerows(v)
data=[r+['']*(len(h)-len(r)) for r in v[1:]]
groups=defaultdict(list)
for r in data:
    if r[I['name']].strip(): groups[(nrm(r[I['legal_entity_id']]),nrm(r[I['name']]))].append(r)
keep=[]; drop_ids=set(); merged=0; exactdup=0; samename_diffcode=[]
for (l,n),rows in groups.items():
    if len(rows)==1: keep.append(rows[0]); continue
    sides=[x[I['Vendor / Customer']].strip() for x in rows]
    codes=[x[I['M3 Code']].strip() for x in rows]
    cust=next((x for x in rows if x[I['Vendor / Customer']].strip()=='Customer'),None)
    vend=next((x for x in rows if x[I['Vendor / Customer']].strip()=='Vendor'),None)
    if cust is not None and vend is not None:  # V+C merge -> keep customer, set both flags
        cust[I['Is Vendor']]='TRUE'; cust[I['Is Customer']]='TRUE'; cust[I['Vendor / Customer']]='Customer'
        cust[I['M3 Vendor Code (for merged vendor & customer)']]=vend[I['M3 Code']].strip()
        keep.append(cust); merged+=1
        # keep any extra rows beyond the one V + one C? (rare) - keep them
        for x in rows:
            if x is not cust and x is not vend: keep.append(x)
    elif len(set(codes))==1:  # exact same-code same-side dup -> keep first
        keep.append(rows[0]); exactdup+=len(rows)-1
    else:  # same name, different code, same side -> keep all (document)
        keep.extend(rows); samename_diffcode.append((n,codes))
print(f"V+C merged pairs={merged} | exact dups removed={exactdup} | same-name/diff-code kept(documented)={len(samename_diffcode)}")
for n,codes in samename_diffcode: print(f"   KEEP-BOTH (why: 2 M3 codes, same name): {n[:40]} {codes}")
print(f"rows {len(data)} -> {len(keep)}")
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range="'Counterparty v2'").execute())
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'Counterparty v2'!A1",valueInputOption='RAW',body={'values':[h]+keep}).execute())
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 8 CPv2 V+C merge 2026-07-01',f'{merged} V+C merged, {exactdup} exact dups removed; {len(samename_diffcode)} same-name/diff-code kept']]}).execute())
print(f"rewrote Counterparty v2 ({len(keep)} rows, backup Counterparty v2.pre-vcmerge.csv)")
