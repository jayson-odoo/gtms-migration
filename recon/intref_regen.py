# -*- coding: utf-8 -*-
"""Regenerate the 'Integration Reference' tab from current Counterparty v2, now carrying an
'Integratable Legal Entity' column so the loader resolves the counterparty by (name+legal_entity)
instead of name alone. 3 cases: customer-only(1 row), vendor-only(1 row), merged(2 rows:
customer M3 Code + vendor M3 Vendor Code). Backup + audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
TYPE='App\\Models\\Counterparty'
HDR=['id','Vendor Reference','Unique / Duplicate','Customer Reference','Integratable Reference','Integratable Legal Entity','Integratable Type']
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
cp=get('Counterparty v2'); h=[c.strip() for c in cp[0]]
def ix(n): return next((i for i,c in enumerate(h) if c.strip().lower()==n.lower()),-1)
sd,mc,mv,ud,nm,le=ix('Vendor / Customer'),ix('M3 Code'),ix('M3 Vendor Code (for merged vendor & customer)'),ix('Unique / Duplicate'),ix('name'),ix('legal_entity_id')
# backup old IR
old=get('Integration Reference')
with open(f"{BK}/Integration Reference.pre-regen.csv",'w',newline='') as f: csv.writer(f).writerows(old)
out=[HDR]; i=1; cust=vend=merged=0
for r in cp[1:]:
    r=r+['']*(len(h)-len(r))
    name=r[nm].strip(); code=r[mc].strip(); side=r[sd].strip(); mvend=r[mv].strip()
    if not name or not code: continue
    u=r[ud].strip() or 'Unique'; lename=r[le].strip()
    if side=='Customer':
        out.append([i,'',u,code,name,lename,TYPE]); i+=1; cust+=1
    else:
        out.append([i,code,u,'',name,lename,TYPE]); i+=1; vend+=1
    if mvend:   # merged -> add the vendor-side row
        out.append([i,mvend,u,'',name,lename,TYPE]); i+=1; merged+=1
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range="'Integration Reference'").execute())
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'Integration Reference'!A1",valueInputOption='RAW',body={'values':out}).execute())
print(f"Integration Reference: {len(old)-1} -> {len(out)-1} rows (customer {cust} + vendor {vend} + merged-vendor {merged})")
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['INTEGRATION REFERENCE REGEN 2026-07-02',f'regenerated from CPv2 w/ Integratable Legal Entity col ({len(out)-1} rows); loader now resolves by (name+legal_entity). backup .pre-regen.csv']]}).execute())
print("audited. Backup Integration Reference.pre-regen.csv")
