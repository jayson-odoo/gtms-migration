# -*- coding: utf-8 -*-
import re, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'
ACC_QLF='Account QL Feed - Master Data (Part 1) 20260627.xlsx'
ACC_QLI='Account QL International - QL Master Data (Part 1 - Trade Customer, Trade Vendor and Legal Entity) submited on 26.06.2026.xlsx'
def norm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
cv=svc.spreadsheets().values().get(spreadsheetId=SID,range="'Counterparty v2'").execute().get('values',[])
h=cv[0]; mi=h.index('M3 Code')
cpset=set(); cpname={}
for r in cv[1:]:
    if mi<len(r) and r[mi].strip():
        k=norm(r[mi]); cpset.add(k); cpname.setdefault(k, dict(zip(h,r)).get('name',''))
print(f"Counterparty v2: {len(cpset)} distinct M3 codes")
SRC=[('Vendor QLF',ACC_QLF,'Vendor',0),('Vendor QLI',ACC_QLI,'Vendor',0),
     ('Customer QLF',ACC_QLF,'Customer',0),('Customer QLI',ACC_QLI,'Customer',0)]
new={}; matched=0; rawtotal=0
for label,f,sh,hd in SRC:
    df=pd.read_excel(f"{DIR}/{f}",sheet_name=sh,header=hd,dtype=str).fillna('')
    for _,r in df.iterrows():
        code=norm(r.get('M3 Code',''))
        if not code: continue
        rawtotal+=1
        if code in cpset: matched+=1
        else:
            new.setdefault(code, [label, r.get('name',''), r.get('legal_entity',''), r.get('type',''), r.get('country','')])
print(f"raw counterparty rows w/ M3: {rawtotal} | matched in CPv2: {matched} | NEW codes: {len(new)}\n")
for code,(lbl,nm,le,ty,co) in sorted(new.items()):
    print(f"  NEW {code:14} [{lbl:12}] {nm[:40]:40} le={le:4} type={ty:9} country={co}")
