# -*- coding: utf-8 -*-
"""Fix M3 Vendor Code + Is Vendor for the 5 V+C entities whose raw vendor code differs from customer code."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
# M3 Code (customer/primary) -> correct raw vendor code
FIX={'QBUNG001QF':'QBUNG002QF','QCARG001QF':'QCARG002QF','QHENG002QF':'QHENG001QF',
     'QLIAN003QF':'QLIAN001QF','QGOLD002QF':'QGOLD002QF'}
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
h=[c.strip() for c in v[0]]; mc=h.index('M3 Code'); mv=h.index('M3 Vendor Code (for merged vendor & customer)'); iv=h.index('Is Vendor')
with open(f"{BK}/Counterparty v2.pre-vendorcodefix.csv",'w',newline='') as f: csv.writer(f).writerows(v)
def colA1(i):
    s=''; i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
ups=[]; done=[]
for ri,r in enumerate(v[1:],start=2):
    r=r+['']*(len(h)-len(r)); code=r[mc].strip()
    if code in FIX:
        ups.append({'range':f"'Counterparty v2'!{colA1(mv)}{ri}",'values':[[FIX[code]]]})
        ups.append({'range':f"'Counterparty v2'!{colA1(iv)}{ri}",'values':[['TRUE']]})
        done.append((code,FIX[code]))
retry(lambda: svc.spreadsheets().values().batchUpdate(spreadsheetId=JAY,body={'valueInputOption':'RAW','data':ups}).execute())
print("fixed rows (M3 Code -> M3 Vendor Code set, Is Vendor=TRUE):")
for c,vc in done: print(f"   {c} -> vendor {vc}")
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 9 CPv2 vendor-code fix 2026-07-01',f'{len(done)} merged rows: set correct raw M3 Vendor Code + Is Vendor']]}).execute())
print("audited.")
