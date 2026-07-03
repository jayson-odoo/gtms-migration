# -*- coding: utf-8 -*-
import csv, time
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
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
bg=retry(lambda: svc.spreadsheets().values().batchGet(spreadsheetId=SID, ranges=["'Products'","'RECON 300626 - Products NEW'"]).execute())['valueRanges']
pv=bg[0].get('values',[]); ph=[h.strip() for h in pv[0]]
sv=bg[1].get('values',[]); sh=[h.strip() for h in sv[2]]; sdata=sv[3:]
with open(f"{BK}/Products.csv",'w',newline='') as f: csv.writer(f).writerows(pv)
resolved=[]; held=[]
for r in sdata:
    d=dict(zip(sh, r+['']*(len(sh)-len(r))))
    if d.get('GTMS Packing Unit','').strip() and d.get('default_uom','').strip(): resolved.append(d)
    else: held.append(d.get('code',''))
rows=[[d.get(h,'') for h in ph] for d in resolved]
retry(lambda: svc.spreadsheets().values().append(spreadsheetId=SID,range="'Products'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows}).execute())
print(f"Products appended: {len(resolved)} (rows {len(pv)-1}->{len(pv)-1+len(resolved)}) | HELD (need packing unit): {held}")
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 2 Products go-live 2026-07-01',f'{len(resolved)} added; held {len(held)}: '+",".join(held)]]}).execute())
print("backed up recon/backup/Products.csv + audited")
