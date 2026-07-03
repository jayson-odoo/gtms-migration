# -*- coding: utf-8 -*-
"""Normalize Counterparty v2 country/billing_country to ISO: SW->CH, SZ->CH, VT->VN. Flag MI. Backup+audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
MAP={'SW':'CH','SZ':'CH','VT':'VN'}
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
h=[c.strip() for c in v[0]]; ci=h.index('country'); bi=h.index('billing_country'); ni=h.index('name')
with open(f"{BK}/Counterparty v2.pre-countrynorm.csv",'w',newline='') as f: csv.writer(f).writerows(v)
n=0; mi=[]; rows=[h]
for r in v[1:]:
    r=r+['']*(len(h)-len(r))
    for col in (ci,bi):
        cv=r[col].strip()
        if cv in MAP: r[col]=MAP[cv]; n+=1
        elif cv=='MI': mi.append(r[ni].strip())
    rows.append(r[:len(h)])
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range="'Counterparty v2'").execute())
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'Counterparty v2'!A1",valueInputOption='RAW',body={'values':rows}).execute())
print(f"normalized {n} country cells (SW/SZ->CH, VT->VN). MI left (flag): {sorted(set(mi))}")
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 7 CPv2 country normalize + reference_2 2026-07-01',f'{n} country cells SW/SZ->CH VT->VN; reference_2 added to update_cols']]}).execute())
print("audited.")
