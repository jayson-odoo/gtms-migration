# -*- coding: utf-8 -*-
"""Complete the pass-2 Payment Term rename: propagate new names to dependent tabs so junctions
resolve to the renamed terms (id51/52) instead of the stale id13/21. Backup + audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
REN={'7 Days':'7 days net','Prompt Payment':'Cash on Delivery (Non AR)'}
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
for tab,col in [('Payment Term Configs','payment_term'),('Payment Term x Profit Center','name')]:
    v=get(tab); h=[x.strip() for x in v[0]]; ci=h.index(col)
    with open(f"{BK}/{tab}.pre-ptrename.csv",'w',newline='') as f: csv.writer(f).writerows(v)
    n=0; rows=[h]
    for r in v[1:]:
        r=r+['']*(len(h)-len(r))
        if r[ci].strip() in REN: r[ci]=REN[r[ci].strip()]; n+=1
        rows.append(r[:len(h)])
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{tab}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{tab}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
    print(f"{tab}: renamed {n} cells (backup {tab}.pre-ptrename.csv)")
