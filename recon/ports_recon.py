# -*- coding: utf-8 -*-
import re, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'; SHIP='Shipping QLI & QLF - Master Data Port.xlsx'
def n(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
jp=svc.spreadsheets().values().get(spreadsheetId=SID,range="'Ports'").execute().get('values',[])
h=jp[0]
jcode={}; jname={}
for r in jp[1:]:
    d=dict(zip(h,r)); c=str(d.get('code','')).strip(); nm=str(d.get('name','')).strip()
    if c: jcode[n(c)]=d
    if nm: jname[n(nm)]=d
print(f"Jayson Ports: {len(jp)-1} rows")
sp=pd.read_excel(f"{DIR}/{SHIP}",sheet_name='Ports',header=0,dtype=str).fillna('')
mc=mn=new=0; newlist=[]; codediff=[]
for _,r in sp.iterrows():
    c=str(r.get('code','')).strip(); nm=str(r.get('name','')).strip()
    if not c and not nm: continue
    if n(c) in jcode: mc+=1
    elif n(nm) in jname:
        mn+=1; jc=jname[n(nm)].get('code','')
        codediff.append((c, jc, nm))
    else:
        new+=1; newlist.append((c,nm,r.get('country',''),r.get('state',''),r.get('region','')))
print(f"Shipping Ports: {len(sp)} | matched by code: {mc} | matched by NAME (diff code): {mn} | NEW: {new}\n")
print("--- code differs (same name) sample ---")
for c,jc,nm in codediff[:12]: print(f"  ship '{c}' vs jayson '{jc}'  {nm[:40]}")
print(f"\n--- NEW ports ({len(newlist)}) ---")
for c,nm,co,st,rg in newlist: print(f"  {c:8} {nm[:38]:38} country={co:4} state={st:16} region={rg}")
