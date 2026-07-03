# -*- coding: utf-8 -*-
"""Remove the 2 wrongly-appended standalone vendor rows QBUNG002QF / QCARG003QF from Counterparty v2.
They are already the 'M3 Vendor Code (for merged vendor & customer)' on existing customer rows
(QBUNG001QF BUNGE AGRIBUSINESS, QCARG002QF CARGILL INTERNATIONAL TRADING) -> Integration Reference
generates the vendor side from there; standalone rows are duplicates. Backup + guard + audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
REMOVE={'QBUNG002QF','QCARG003QF'}
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=SID).execute())
gid=next(s['properties']['sheetId'] for s in meta['sheets'] if s['properties']['title']=='Counterparty v2')
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'Counterparty v2'").execute()).get('values',[])
hdr=[c.strip() for c in v[0]]; mc=hdr.index('M3 Code'); vc=hdr.index('Vendor / Customer'); nm=hdr.index('name')
# full backup of current state for THIS op
with open(f"{BK}/Counterparty v2.pre-dedup.csv",'w',newline='') as f: csv.writer(f).writerows(v)
# locate target rows (must be Vendor + M3 in REMOVE); collect 1-based row numbers
targets=[]
for ri,r in enumerate(v[1:],start=2):
    if (r[mc].strip() if len(r)>mc else '') in REMOVE and (r[vc].strip() if len(r)>vc else '').lower()=='vendor':
        targets.append((ri, r[mc].strip(), r[nm].strip() if len(r)>nm else ''))
print("rows to delete:", targets)
assert len(targets)==2, f"expected 2 targets, found {len(targets)} - abort"
# delete descending so indices don't shift; sheet row N (1-based) = dimension index N-1
reqs=[{'deleteDimension':{'range':{'sheetId':gid,'dimension':'ROWS','startIndex':ri-1,'endIndex':ri}}}
      for ri,_,_ in sorted(targets, reverse=True)]
retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':reqs}).execute())
after=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'Counterparty v2'").execute()).get('values',[])
print(f"deleted 2 rows. Counterparty v2 {len(v)-1} -> {len(after)-1} data rows (backup recon/backup/Counterparty v2.pre-dedup.csv)")
# audit
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'RECON 300626 - Applied'").execute()).get('values',[])
note=[['PASS 2 Counterparty v2 DEDUP 2026-07-01',
       'Removed 2 wrongly-appended standalone vendors QBUNG002QF/QCARG003QF - already merged-vendor codes on existing customer rows QBUNG001QF/QCARG002QF. 447->445.']]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
print("audited.")
