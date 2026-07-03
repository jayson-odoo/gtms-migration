# -*- coding: utf-8 -*-
"""(1) Delete jayson-only 'Port Container Shifting / FCL' from Additonal Costs (follow raw = keep only
20 FCL / 40 FCL). (2) Rename DMX spec group 'LOCAL - MALAYSIA DMX-7 MOLD INHIBITOR' -> '...DMX PLUS...'
to follow raw product (DMX PLUS = TGQDMXPL) across SpecGroup/Spec Group Spec/Spec Group x Product/SpecGroupFIP.
Backup + audit. Sheet-only (DB stale cleanup is separate)."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
FCL='Port Container Shifting / FCL'
OLD='LOCAL - MALAYSIA DMX-7 MOLD INHIBITOR'; NEW='LOCAL - MALAYSIA DMX PLUS MOLD INHIBITOR'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def rewrite(t,rows):
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{t}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{t}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
def colA1(i):
    s='';i+=1
    while i:i,r=divmod(i-1,26);s=chr(65+r)+s
    return s

# (1) delete FCL row
v=get('Additonal Costs'); h=[c.strip() for c in v[0]]; ni=h.index('name')
with open(f"{BK}/Additonal Costs.pre-fcldel.csv",'w',newline='') as f: csv.writer(f).writerows(v)
out=[h]; deleted=0
for r in v[1:]:
    r=r+['']*(len(h)-len(r))
    if r[ni].strip()==FCL: deleted+=1; continue
    if any(x.strip() for x in r): out.append(r)
rewrite('Additonal Costs',out); print(f"Additonal Costs: deleted {deleted} '{FCL}' row -> {len(out)-1} rows")

# (2) rename DMX-7 -> DMX PLUS across 4 tabs
for tab,col in [('SpecGroup','name'),('Spec Group Spec','SpecGroupName2'),('Spec Group x Product','spec_group'),('SpecGroupFIP','SpecGroupName')]:
    v=get(tab)
    if not v: print(f"{tab}: empty"); continue
    hh=[c.strip() for c in v[0]]
    if col not in hh: print(f"{tab}: no {col}"); continue
    ci=hh.index(col); ups=[]
    with open(f"{BK}/{tab}.pre-dmxrename.csv",'w',newline='') as f: csv.writer(f).writerows(v)
    for ri,r in enumerate(v[1:],2):
        r=r+['']*(len(hh)-len(r))
        if r[ci].strip()==OLD: ups.append({'range':f"'{tab}'!{colA1(ci)}{ri}",'values':[[NEW]]})
    if ups: retry(lambda: svc.spreadsheets().values().batchUpdate(spreadsheetId=JAY,body={'valueInputOption':'RAW','data':ups}).execute())
    print(f"{tab}.{col}: renamed {len(ups)} cell(s) DMX-7 -> DMX PLUS")
print("DONE (backups *.pre-fcldel.csv / *.pre-dmxrename.csv)")
