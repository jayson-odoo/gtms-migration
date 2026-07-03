# -*- coding: utf-8 -*-
"""Restore 3 QLF vendor-only entities lost when name-overwrite matched by ambiguous M3 code:
BUNGE S.A. (QBUNG001QF), CARGILL FEED SDN BHD (QCARG001QF), HENG SOON HEE (QHENG002QF).
Add as Vendor rows from raw Vendor tab. Backup + audit."""
import re, csv, time, glob
import openpyxl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'; BK='/home/src/recon/backup'
ADD={'QBUNG001QF','QCARG001QF','QHENG002QF'}; LE='QL Feed Sdn. Bhd.'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def clean(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def g(r,n):
    for k in r.index:
        if k.strip().lower()==n.lower():
            x=str(r[k]).strip(); return '' if x.lower()=='nan' else x
    return ''
import pandas as pd
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Account QL Feed' in x][0]
df=pd.read_excel(f, sheet_name='Vendor', header=0, dtype=str).fillna('')
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
hdr=[c.strip() for c in v[0]]
with open(f"{BK}/Counterparty v2.pre-vendoronly.csv",'w',newline='') as f2: csv.writer(f2).writerows(v)
rows=[]
for _,r in df.iterrows():
    code=g(r,'M3 Code')
    if code not in ADD: continue
    nm=g(r,'name'); d={c:'' for c in hdr}
    d.update({'Vendor / Customer':'Vendor','Is Vendor':'TRUE','Is Customer':'','M3 Code':code,
      'M3 code + Vendor / Customer':'Vendor'+code,'Unique / Duplicate':'Unique','duplicated_cleaned_name':'Unique',
      'cleaned_name':clean(nm),'name':nm,'long_name':g(r,'long_name') or nm,'legal_entity_id':LE,
      'company_registration_number':g(r,'company_registration_number'),'tax_registration_number':g(r,'tax_registration_number'),
      'tin_no':g(r,'tin_no'),'type':g(r,'type'),'address':g(r,'address'),'country':g(r,'country'),
      'exist_in_countries':g(r,'country'),'billing_address':g(r,'billing_address'),'billing_country':g(r,'billing_country'),
      'phone':g(r,'phone'),'fax':g(r,'fax'),'website':g(r,'website'),'reference_1':g(r,'reference_1'),
      'reference_2':g(r,'reference_2'),'is_internal':'FALSE','is_active':'TRUE'})
    rows.append([d.get(c,'') for c in hdr]); print(f"   + Vendor {code} {nm}")
retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'Counterparty v2'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows}).execute())
print(f"appended {len(rows)} vendor-only rows (backup Counterparty v2.pre-vendoronly.csv)")
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 10 CPv2 restore 3 vendor-only 2026-07-01','BUNGE S.A./CARGILL FEED/HENG SOON HEE lost to M3-code-ambiguity overwrite']]}).execute())
print("audited.")
