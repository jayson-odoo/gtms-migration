# -*- coding: utf-8 -*-
import re, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'; SALES='Sales QLI & QLF - GTMS_INVENTORY LOCATION_290626.xlsx'
def n(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
ji=svc.spreadsheets().values().get(spreadsheetId=SID,range="'Inventory Locations'").execute().get('values',[])
h=ji[0]
jname={}; jcode={}
for r in ji[1:]:
    d=dict(zip(h,r)); nm=str(d.get('name','')).strip(); c=str(d.get('code','')).strip()
    if nm: jname[n(nm)]=d
    if c: jcode[n(c)]=d
print(f"Jayson Inventory Locations: {len(ji)-1} rows | cols={h}\n")
for sh in ['Inventory Locations_QLF_29.6.26','Inventory Locations_QLI_29.6.26']:
    df=pd.read_excel(f"{DIR}/{SALES}",sheet_name=sh,header=0,dtype=str).fillna('')
    mn=newc=0; newlist=[]
    for _,r in df.iterrows():
        nm=str(r.get('name','')).strip(); code=str(r.get('M3 Code','')).strip()
        if not nm: continue
        if n(nm) in jname: mn+=1
        else: newc+=1; newlist.append((code,nm,r.get('legal_entity',''),r.get('Port Code',''),r.get('Location Type','')))
    print(f"[{sh}] rows={len(df)} matched-by-name={mn} NEW={newc}")
    for code,nm,le,pc,lt in newlist: print(f"    NEW {code:6} {nm[:34]:34} le={le:5} port={pc:6} type={lt}")
