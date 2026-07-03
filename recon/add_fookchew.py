# -*- coding: utf-8 -*-
"""Add new customer FOOK CHEW SDN BHD (QFOOK001QF, QL Feed) to Counterparty v2 (present in raw, missing
in jayson). Clone a QLF customer-only row for structure, override from raw. Backup + audit."""
import re, csv, glob, time
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'; BK='/home/src/recon/backup'
CODE='QFOOK001QF'
def clean(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def val(x):
    x=str(x).strip(); return '' if x.lower()=='nan' else x
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Account QL Feed' in x][0]
rdf=pd.read_excel(f,sheet_name='Customer',header=0,dtype=str).fillna('')
rr=next(r for _,r in rdf.iterrows() if val(r['M3 Code'])==CODE)
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
h=[c.strip() for c in v[0]]; H={c:i for i,c in enumerate(h)}
assert not any((r+['']*(len(h)-len(r)))[H['M3 Code']].strip()==CODE for r in v[1:]), "already present"
with open(f"{BK}/Counterparty v2.pre-fookchew.csv",'w',newline='') as fp: csv.writer(fp).writerows(v)
# clone a QLF customer-only row
def is_qlf_custonly(r):
    r=r+['']*(len(h)-len(r))
    return r[H['Is Customer']].strip().upper()=='TRUE' and r[H['Is Vendor']].strip().upper()!='TRUE' and 'QL FEED' in r[H['legal_entity_id']].strip().upper()
sib=next(list(r)+['']*(len(h)-len(r)) for r in v[1:] if is_qlf_custonly(r))
row=sib[:]
nm=val(rr['name'])
def setc(col,x):
    if col in H: row[H[col]]=x
setc('M3 Code',CODE); setc('M3 code + Vendor / Customer','Customer'+CODE)
setc('Vendor / Customer','Customer'); setc('Is Customer','TRUE'); setc('Is Vendor','')
setc('Unique / Duplicate','Unique'); setc('duplicated_cleaned_name','Unique'); setc('cleaned_name',clean(nm))
setc('name',nm); setc('long_name',val(rr['long_name']) or nm)
setc('company_registration_number',val(rr.get('company_registration_number',''))); setc('tax_registration_number',val(rr.get('tax_registration_number','')))
setc('tin_no',val(rr.get('tin_no',''))); setc('type',val(rr.get('type','')) or 'External')
setc('address',val(rr['address'])); setc('country',val(rr['country'])); setc('exist_in_countries',val(rr['country']))
setc('billing_address',val(rr['billing_address'])); setc('billing_country',val(rr['billing_country']))
setc('phone',val(rr['phone'])); setc('fax',val(rr['fax'])); setc('website',val(rr.get('website','')))
setc('reference_1',''); setc('reference_2',''); setc('M3 Vendor Code (for merged vendor & customer)','')
setc('is_internal','FALSE'); setc('is_active','TRUE')
retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'Counterparty v2'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':[row]}).execute())
print(f"+ Customer {CODE} '{nm}' (legal_entity_id={row[H['legal_entity_id']]})")
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['ADD FOOK CHEW 2026-07-02',f'+customer {CODE} FOOK CHEW SDN BHD (new raw customer). backup Counterparty v2.pre-fookchew.csv']]}).execute())
print("audited.")
