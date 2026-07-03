# -*- coding: utf-8 -*-
import re, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'
ACC_QLF='Account QL Feed - Master Data (Part 1) 20260627.xlsx'
ACC_QLI='Account QL International - QL Master Data (Part 1 - Trade Customer, Trade Vendor and Legal Entity) submited on 26.06.2026.xlsx'
NEW=['QBUNG002QF','QCARG003QF','QFYSD001QF','QGRAI001QI','QHONG001QI','QJCSU001QF','QNUSA001QI',
     'QPTTO001QI','QQLLP001QF','QSUCR001QF','QTGLU001QI','QVIAT001QF','QWHEA001QI']
LE={'QLF':'QL Feed Sdn. Bhd.','QLI':'QL International Pte Ltd'}
def norm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
def g(r,c): return str(r.get(c,'')).strip()

# index raw rows by code, capturing side(s)
SRC=[('Vendor',ACC_QLF,'Vendor',0),('Vendor',ACC_QLI,'Vendor',0),('Customer',ACC_QLF,'Customer',0),('Customer',ACC_QLI,'Customer',0)]
rows={}; sides={}
for side,f,sh,hd in SRC:
    df=pd.read_excel(f"{DIR}/{f}",sheet_name=sh,header=hd,dtype=str).fillna('')
    for _,r in df.iterrows():
        code=norm(r.get('M3 Code',''))
        if code in NEW:
            sides.setdefault(code,set()).add(side)
            if code not in rows: rows[code]=r  # first occurrence holds full detail

svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
hdr=svc.spreadsheets().values().get(spreadsheetId=SID,range="'Counterparty v2'!1:1").execute()['values'][0]
hdr=[h.strip() for h in hdr]

def build_row(code):
    r=rows[code]; sd=sides[code]; le=g(r,'legal_entity'); lename=LE.get(le.upper(),le)
    primary='Vendor' if 'Vendor' in sd else 'Customer'
    nm=g(r,'name'); cleaned=re.sub(r'\s+','',nm).upper()
    d={c:'' for c in hdr}
    d.update({
     'Vendor / Customer': ' & '.join(sorted(sd)) if len(sd)>1 else primary,
     'Is Vendor':'TRUE' if 'Vendor' in sd else '', 'Is Customer':'TRUE' if 'Customer' in sd else '',
     'M3 Code':code, 'M3 code + Vendor / Customer': primary+code,
     'Unique / Duplicate':'Unique','duplicated_cleaned_name':'Unique','cleaned_name':cleaned,
     'name':nm,'long_name':g(r,'long_name') or nm,'legal_entity_id':lename,
     'company_registration_number':g(r,'company_registration_number'),
     'tax_registration_number':g(r,'tax_registration_number'),'tin_no':g(r,'tin_no'),
     'type':g(r,'type'),'address':g(r,'address'),'country':g(r,'country'),
     'exist_in_countries':g(r,'country'),'billing_address':g(r,'billing_address'),
     'billing_country':g(r,'billing_country'),'phone':g(r,'phone'),'fax':g(r,'fax'),
     'website':g(r,'website'),'reference_1':g(r,'reference_1'),'reference_2':g(r,'reference_2'),
     'is_internal':'FALSE','is_active':'TRUE'})
    return d

built=[build_row(c) for c in NEW]
print(f"{'CODE':12} {'SIDE':14} {'NAME':38} {'LE':22} {'TYPE':9} {'CTRY':4} {'is_int'}")
for d in built:
    print(f"{d['M3 Code']:12} {d['Vendor / Customer']:14} {d['name'][:38]:38} {d['legal_entity_id']:22} {d['type']:9} {d['country']:4} {d['is_internal']}")

# write preview tab
title='RECON 300626 - CPv2 Adds'
meta=svc.spreadsheets().get(spreadsheetId=SID).execute()
if title not in [s['properties']['title'] for s in meta['sheets']]:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
svc.spreadsheets().values().clear(spreadsheetId=SID,range=f"'{title}'").execute()
banner='PREVIEW of 13 new counterparties to APPEND to Counterparty v2 (NOT yet appended). Full CPv2 schema; Unique/Duplicate=Unique, is_internal=FALSE, is_active=TRUE. legal_entity_id uses full LE name.'
vals=[[banner],[],hdr]+[[d[c] for c in hdr] for d in built]
svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':vals}).execute()
print(f"\nwrote preview tab '{title}' with {len(built)} rows. (append step is separate)")
