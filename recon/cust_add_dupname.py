# -*- coding: utf-8 -*-
"""Add the 2 missing customer name-variants that share an M3 code with an existing CPv2 row
(user decision: capture all 307 raw customers; counterparty guard is (legal_entity,lower(name)),
so a shared M3 code is fine here — code only matters for Integration Reference).
Clone the existing same-code sibling row, override name + raw-sourced identity fields. Backup + audit."""
import re, csv, glob, time
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
D='/home/src/raw_master/300626'; BK='/home/src/recon/backup'
# (M3 code, raw name to add)
ADD=[('QSWKH001QF','SWKHEW AGRICULTURE SDN.BHD.'),('QYENH001QF','YENHER AGRO-PRODUCTS SDN BHD')]
def clean(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def val(x):
    x=str(x).strip(); return '' if x.lower()=='nan' else x
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
# raw source rows
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Account QL Feed' in x][0]
rdf=pd.read_excel(f,sheet_name='Customer',header=0,dtype=str).fillna('')
def rawrow(code,name):
    for _,r in rdf.iterrows():
        if val(r['M3 Code'])==code and val(r['name'])==name: return r
    raise SystemExit(f'raw row not found: {code} {name}')
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
h=[c.strip() for c in v[0]]; H={c:i for i,c in enumerate(h)}
with open(f"{BK}/Counterparty v2.pre-custdup.csv",'w',newline='') as fp: csv.writer(fp).writerows(v)
def sibling(code):
    for r in v[1:]:
        r=r+['']*(len(h)-len(r))
        if r[H['M3 Code']].strip()==code and r[H['Is Customer']].strip().upper()=='TRUE': return list(r)
    raise SystemExit(f'no sibling for {code}')
def setc(row,col,x):
    if col in H: row[H[col]]=x
newrows=[]
for code,name in ADD:
    row=sibling(code)[:]; rr=rawrow(code,name)
    setc(row,'name',name); setc(row,'long_name',val(rr['long_name']) or name)
    setc(row,'cleaned_name',clean(name))
    setc(row,'M3 code + Vendor / Customer','Customer'+code)
    setc(row,'Unique / Duplicate','Duplicate')          # shares M3 code
    setc(row,'address',val(rr['address'])); setc(row,'country',val(rr['country']))
    setc(row,'exist_in_countries',val(rr['country']))
    setc(row,'billing_address',val(rr['billing_address'])); setc(row,'billing_country',val(rr['billing_country']))
    setc(row,'phone',val(rr['phone'])); setc(row,'fax',val(rr['fax']))
    setc(row,'company_registration_number',val(rr.get('company_registration_number','')))
    setc(row,'tax_registration_number',val(rr.get('tax_registration_number','')))
    setc(row,'tin_no',val(rr.get('tin_no','')))
    newrows.append(row); print(f"   + Customer {code} '{name}' (legal_entity_id={row[H['legal_entity_id']]})")
retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'Counterparty v2'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':newrows}).execute())
print(f"appended {len(newrows)} customer name-variant rows (backup Counterparty v2.pre-custdup.csv)")
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['CUST DUP-NAME ADD 2026-07-01','+2 customer name-variants sharing M3 code (SWKHEW AGRICULTURE/YENHER AGRO-PRODUCTS); guard=legal_entity+lower(name), code only matters for Integration Reference; -> 307 customers']]}).execute())
print("audited.")
