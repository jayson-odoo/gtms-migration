# -*- coding: utf-8 -*-
import re, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'
PUR='Purchasing QL Feed  QL International - QL Master Data (Part 1) 20260629.xlsx'
SHIP='Shipping QLI & QLF - Master Data Port.xlsx'
def n(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def banner(s):
    s=str(s).upper()
    return any(w in s for w in ['SDN BHD','SELLER','PURCHASE CONTRACT','PURCHASING','QL FEED','QL INTERNATIONAL','PTE LTD']) or len(str(s))>40
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def jget(t):
    v=svc.spreadsheets().values().get(spreadsheetId=SID,range=f"'{t}'").execute().get('values',[])
    return v[0],[dict(zip(v[0],r)) for r in v[1:]]

# ---- Products ----
ph,pj=jget('Products')
jids=set()
for d in pj:
    for c in ('code','contract_number_reference','description'): jids.add(n(d.get(c,'')))
jids.discard('')
rp=pd.read_excel(f"{DIR}/{PUR}",sheet_name='Products',header=0,dtype=str).fillna('')
pnew=[]
for _,r in rp.iterrows():
    code=str(r.get('M3 Code','')).strip(); desc=str(r.get('description','')).strip()
    if not code or banner(code): continue
    if n(code) in jids or n(r.get('contract_number_reference','')) in jids or n(desc) in jids: continue
    pnew.append((code, desc[:40]))
print(f"PRODUCTS: Jayson={len(pj)} raw={len(rp)} | candidate-new={len(pnew)}")
for c,d in pnew[:40]: print(f"    {c:16} {d}")

# ---- SpecGroup ----
sh,sj=jget('SpecGroup')
jg=set(n(d.get('name','')) for d in sj); jg.discard('')
rs=pd.read_excel(f"{DIR}/{PUR}",sheet_name='SpecGroup',header=0,dtype=str).fillna('')
gcol='SpecGroupName2'
seen=set(); snew=[]
for _,r in rs.iterrows():
    g=str(r.get(gcol,'')).strip()
    if not g or banner(g): continue
    if n(g) in seen: continue
    seen.add(n(g))
    if n(g) not in jg: snew.append(g)
print(f"\nSPECGROUP: Jayson groups={len(jg)} raw distinct groups={len(seen)} | candidate-new={len(snew)}")
for g in snew[:40]: print(f"    {g[:60]}")

# ---- Charges (Additonal Costs) ----
ah,aj=jget('Additonal Costs')
ja=set(n(d.get('name','')) for d in aj); ja.discard('')
ra=pd.read_excel(f"{DIR}/{PUR}",sheet_name='Additional Charges',header=0,dtype=str).fillna('')
seen=set(); anew=[]
for _,r in ra.iterrows():
    nm=str(r.get('Name','')).strip()
    if not nm or banner(nm): continue
    if n(nm) in seen: continue
    seen.add(n(nm))
    if n(nm) not in ja: anew.append(nm)
print(f"\nADDITIONAL CHARGES vs 'Additonal Costs': Jayson={len(aj)} raw distinct={len(seen)} | candidate-new={len(anew)}")
for a in anew[:40]: print(f"    {a[:60]}")

# ---- write candidates to a review tab ----
title='RECON 300626 - PSC Candidates'
meta=svc.spreadsheets().get(spreadsheetId=SID).execute()
if title not in [s['properties']['title'] for s in meta['sheets']]:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
svc.spreadsheets().values().clear(spreadsheetId=SID,range=f"'{title}'").execute()
out=[['Candidate-new items from raw not found in Jayson by name/code (NEEDS DOMAIN REVIEW: some are origin-variants already present under TGQ codes, some are junk). Nothing applied.'],[]]
out+=[[f'PRODUCTS candidate-new ({len(pnew)})','raw M3 Code','description']]
out+=[['',c,d] for c,d in pnew]
out+=[[]]
out+=[[f'SPECGROUP candidate-new groups ({len(snew)})','group name']]
out+=[['',g] for g in snew]
out+=[[]]
out+=[[f'ADDITIONAL CHARGES candidate-new ({len(anew)})','name']]
out+=[['',a] for a in anew]
svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':out}).execute()
print(f"\nwrote review tab '{title}'")
