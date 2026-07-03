# -*- coding: utf-8 -*-
"""Add the 49%-grade HI-PRO DDGS spec group (raw HI-PRO DISTILLERS DRIED GRAIN WITH SOLUBLES has TWO
grade tiers; jayson only had the 48%). New group + its 8 numeric spec lines. Backup + audit.
Product link (Spec Group x Product) left for user to confirm (TGQDDGSHP) - existing 48% group is also unlinked."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
NAME='HI-PRO DISTILLERS DRIED GRAIN WITH SOLUBLES (49% PROTEIN)'
DESC='Crude Protein 49.00% Min, Crude Fat 5.00% Min, Fiber 8.00% Max, Moisture 11.00% Max, Ash 8.00% Max, Vomitoxin 5 PPM Max, Aflatoxin 20 PPB Max, Hunter L Color Score 50 Min.'
# SpecName -> (minimum, maximum)  (numeric-only per model; blanks where n/a)
SPECS=[('Crude Protein','49.0',''),('Crude Fat','5.0',''),('Fiber','','8.0'),('Moisture','','11.0'),
       ('Ash','','8.0'),('Vomitoxin','','5.0'),('Aflatoxin','','20.0'),('Hunter L Color Score','50.0','')]
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
# ---- SpecGroup: append id 86 ----
sg=get('SpecGroup'); sgh=[c.strip() for c in sg[0]]
with open(f"{BK}/SpecGroup.pre-ddgs49.csv",'w',newline='') as f: csv.writer(f).writerows(sg)
assert NAME not in [r[1].strip() for r in sg[1:] if len(r)>1], "group already exists"
newid=str(max(int(r[0]) for r in sg[1:] if r and r[0].strip().isdigit())+1)
sgrow={'id':newid,'name':NAME,'description':DESC,'sales_spec_group_description':DESC,'is_active':'TRUE'}
retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'SpecGroup'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':[[sgrow.get(c,'') for c in sgh]]}).execute())
print(f"SpecGroup: +1 row id={newid} '{NAME}'")
# ---- Spec Group Spec: append 8 spec lines ----
gs=get('Spec Group Spec'); gh=[c.strip() for c in gs[0]]
with open(f"{BK}/Spec Group Spec.pre-ddgs49.csv",'w',newline='') as f: csv.writer(f).writerows(gs)
rows=[]
for sn,mn,mx in SPECS:
    d={'SpecGroupName2':NAME,'SpecName':sn,'minimum':mn,'maximum':mx,'is_derived':'FALSE'}
    rows.append([d.get(c,'') for c in gh])
retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'Spec Group Spec'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows}).execute())
print(f"Spec Group Spec: +{len(rows)} spec lines for '{NAME}'")
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['HI-PRO DDGS 49% GRADE ADD 2026-07-02',f'raw had 2 grade tiers; added 49%-grade SpecGroup (id {newid}) + 8 spec lines. Product link TGQDDGSHP pending user confirm (48% group also unlinked).']]}).execute())
print("audited. SpecGroup 85->86, spec lines +8. NOTE: DB migration pending tunnel; product link pending confirm.")
