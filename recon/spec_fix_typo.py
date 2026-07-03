# -*- coding: utf-8 -*-
"""Fix jayson typo 'Sand in HCI insolible' -> 'Sand in HCl insoluble' (correct chemistry: HCl, insoluble),
matching the raw spelling, in Specifications master (FK) + Spec Group Spec rows. Backup + audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
BAD='Sand in HCI insolible'; GOOD='Sand in HCl insoluble'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def colA1(i):
    s=''; i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
ups=[]
for tab,col in [('Specifications','name'),('Spec Group Spec','SpecName')]:
    v=get(tab); h=[c.strip() for c in v[0]]; ci=h.index(col)
    with open(f"{BK}/{tab}.pre-typofix.csv",'w',newline='') as f: csv.writer(f).writerows(v)
    n=0
    for ri,r in enumerate(v[1:],start=2):
        r=r+['']*(len(h)-len(r))
        if r[ci].strip()==BAD:
            ups.append({'range':f"'{tab}'!{colA1(ci)}{ri}",'values':[[GOOD]]}); n+=1
    print(f"{tab}: {n} cell(s) to fix")
retry(lambda: svc.spreadsheets().values().batchUpdate(spreadsheetId=JAY,body={'valueInputOption':'RAW','data':ups}).execute())
print(f"fixed {len(ups)} cells '{BAD}' -> '{GOOD}' (backups *.pre-typofix.csv)")
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['SPEC TYPO FIX 2026-07-02',f"'{BAD}' -> '{GOOD}' in Specifications + Spec Group Spec ({len(ups)} cells)"]]}).execute())
print("audited.")
