# -*- coding: utf-8 -*-
"""Apply 7 safe blank-fills to live 'Additonal Costs' default_value (only where currently blank).
Backup + audit. Additive fill-blank only."""
import re, csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def N(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
FILLS={ 'ADMIN FEES – NCD SCHEME':'30','ELECTRONIC DATA FUNDED TRANSFER':'30',
    'ELECTRONIC DATA INTERCHARGES':'31.8','CARPENTRY – OGA':'65','EXTRA MOVE CHARGES – EMC':'100',
    'QUARANTINE–AGRICULTURE DEPT.':'100','REMOVAL CHARGES':'65' }
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def colA1(i):
    s=''; i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'Additonal Costs'").execute()).get('values',[])
h=[c.strip() for c in v[0]]; ni=h.index('name'); dvi=h.index('default_value'); dvcol=colA1(dvi)
with open(f"{BK}/Additonal Costs.csv",'w',newline='') as f: csv.writer(f).writerows(v)
updates=[]; done=[]; skipped=[]
for ri,r in enumerate(v[1:],start=2):
    nm=r[ni].strip() if len(r)>ni else ''
    key=N(nm)
    if key not in FILLS: continue
    cur=r[dvi].strip() if len(r)>dvi else ''
    if cur:  # blank-guard: never overwrite an existing value
        skipped.append((nm,cur)); continue
    newv=f"{float(FILLS[key]):.2f}"
    updates.append({'range':f"'Additonal Costs'!{dvcol}{ri}",'values':[[newv]]}); done.append((nm,newv))
if updates:
    retry(lambda: svc.spreadsheets().values().batchUpdate(spreadsheetId=SID,body={'valueInputOption':'RAW','data':updates}).execute())
print(f"filled {len(done)} blank default_value cells (backup recon/backup/Additonal Costs.csv):")
for nm,nv in done: print(f"   {nm:36} -> {nv}")
missing=[k for k in FILLS if k not in {N(r[ni]) for r in v[1:] if len(r)>ni}]
if skipped: print("SKIPPED (already had a value):", skipped)
if missing: print("NOT FOUND in sheet:", missing)
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'RECON 300626 - Applied'").execute()).get('values',[])
note=[['PASS 2 Charges blank-fills 2026-07-01', f'{len(done)} default_value filled: '+", ".join(f"{n}={x}" for n,x in done)]]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
print("audited.")
