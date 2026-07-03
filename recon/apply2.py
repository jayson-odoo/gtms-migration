# -*- coding: utf-8 -*-
"""Pass-2 held-item applies: Payment Term PP/7D names (raw) + consistent QLI legal-entity
rename across live FK tabs. Backs up each modified tab to recon/backup/. Logs to audit tab."""
import csv, re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def col_a1(i):
    s=''; i+=1
    while i>0: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
def get(t): return svc.spreadsheets().values().get(spreadsheetId=SID,range=f"'{t}'").execute().get('values',[])
def backup(t,vals):
    with open(f"{BK}/{t}.csv",'w',newline='') as fp: csv.writer(fp).writerows(vals)

DOT='QL International Pte. Ltd.'; NODOT='QL International Pte Ltd'
CASCADE=['Legal Entity','Profit Centers','Counterparty v2','Inventory Locations','Legal Entity x Tax','Legal Entity x Contract Type']
applied=[]

# 1) QLI name cascade (exact string replace)
for t in CASCADE:
    vals=get(t); backup(t,vals); data=[]
    for ri,row in enumerate(vals[1:], start=2):
        for ci,c in enumerate(row):
            if str(c).strip()==DOT:
                data.append({'range':f"'{t}'!{col_a1(ci)}{ri}",'values':[[NODOT]]})
                applied.append((t, f"{col_a1(ci)}{ri}", DOT+' -> '+NODOT))
    if data:
        svc.spreadsheets().values().batchUpdate(spreadsheetId=SID,body={'valueInputOption':'RAW','data':data}).execute()
    print(f"{t}: {len(data)} cells renamed")

# 2) Payment Term PP/7D names (raw)
pt=get('Payment Term')
if 'Payment Term.csv' not in __import__('os').listdir(BK): backup('Payment Term', pt)  # may already exist from pass1
h=pt[0]; idc=h.index('id'); namec=h.index('name')
ptmap={'PP':'Cash on Delivery (Non AR)','7D':'7 days net'}
data=[]
for ri,row in enumerate(pt[1:], start=2):
    if idc<len(row) and row[idc].strip() in ptmap:
        v=ptmap[row[idc].strip()]
        data.append({'range':f"'Payment Term'!{col_a1(namec)}{ri}",'values':[[v]]})
        applied.append(('Payment Term', f"{col_a1(namec)}{ri}", f"name -> {v}"))
if data:
    svc.spreadsheets().values().batchUpdate(spreadsheetId=SID,body={'valueInputOption':'RAW','data':data}).execute()
print(f"Payment Term: {len(data)} name cells set")

# audit append
title='RECON 300626 - Applied'
cur=get(title)
rows=cur+[[]]+[['PASS 2 held-items 2026-07-01','','']]+[['tab','cell','change']]+[list(a) for a in applied]
svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':rows}).execute()
print(f"\nTOTAL pass-2 held applies: {len(applied)}")
