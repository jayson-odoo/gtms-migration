# -*- coding: utf-8 -*-
"""Apply the confirmed safe UPDATE set to Jayson data tabs. Backs up each tab to
recon/backup/<tab>.csv first. Field updates only (no new rows, no deletes). Logs to a tab."""
import re, csv, os, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
OUT='/home/src/recon/out'; BK='/home/src/recon/backup'
creds=Credentials.from_service_account_file(KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc=build('sheets','v4',credentials=creds,cache_discovery=False)

KEYCOL={'Legal Entity':'code','Payment Term':'id','Packing Unit':'original_code'}
def norm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
def col_a1(i):
    s=''; i+=1
    while i>0: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s

# build change list: APPLY rows minus name-field, plus QLI currency USD
cp=pd.read_csv(f"{OUT}/changeplan.csv").fillna('')
changes=[]
for _,r in cp[cp['recommend']=='APPLY'].iterrows():
    if r['field']=='name': continue
    changes.append((r['entity'], str(r['key']), r['field'], str(r['raw_value'])))
changes.append(('Legal Entity','QLI','currency','USD'))

applied=[]; missing=[]
by_tab={}
for e,k,f,v in changes: by_tab.setdefault(e,[]).append((k,f,v))

for tab, ch in by_tab.items():
    vr=svc.spreadsheets().values().get(spreadsheetId=SID, range=f"'{tab}'").execute()
    vals=vr.get('values',[])
    hdr=[str(c).strip() for c in vals[0]]
    # backup
    with open(f"{BK}/{tab}.csv",'w',newline='') as fp:
        w=csv.writer(fp); w.writerows(vals)
    kc=hdr.index(KEYCOL[tab])
    # row map
    rowmap={}
    for i,row in enumerate(vals[1:], start=2):
        if kc < len(row):
            kk=norm(row[kc])
            if kk and kk not in rowmap: rowmap[kk]=i
    data=[]
    for k,f,v in ch:
        kk=norm(k)
        if kk not in rowmap: missing.append((tab,k,f)); continue
        if f not in hdr: missing.append((tab,k,f+'(no col)')); continue
        rn=rowmap[kk]; ci=hdr.index(f)
        data.append({'range':f"'{tab}'!{col_a1(ci)}{rn}", 'values':[[v]]})
        applied.append((tab,k,f,v))
    if data:
        svc.spreadsheets().values().batchUpdate(spreadsheetId=SID,
            body={'valueInputOption':'RAW','data':data}).execute()
    print(f"{tab}: applied {len(data)} cells, backed up {len(vals)} rows -> recon/backup/{tab}.csv")

print(f"\nTOTAL applied: {len(applied)} | missing: {len(missing)}")
for m in missing: print("  MISSING:", m)

# audit log tab
title='RECON 300626 - Applied'
meta=svc.spreadsheets().get(spreadsheetId=SID).execute()
if title not in [s['properties']['title'] for s in meta['sheets']]:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
svc.spreadsheets().values().clear(spreadsheetId=SID, range=f"'{title}'").execute()
log=[['Applied safe UPDATE set on 2026-07-01 (pass 1). Tabs backed up to recon/backup/. New rows + name flips + seed re-adds held.'],[],
     ['tab','key','field','new_value']]+[list(a) for a in applied]
svc.spreadsheets().values().update(spreadsheetId=SID, range=f"'{title}'!A1", valueInputOption='RAW', body={'values':log}).execute()
print(f"wrote audit tab '{title}'")
