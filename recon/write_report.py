# -*- coding: utf-8 -*-
"""Write the read-only reconciliation report into the Jayson sheet as TWO NEW tabs
(non-destructive): 'RECON 300626 - Summary' and 'RECON 300626 - Details'."""
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
OUT='/home/src/recon/out'
creds=Credentials.from_service_account_file(KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc=build('sheets','v4',credentials=creds,cache_discovery=False)

NOTES={
 ('Products','Purchasing QL Feed  QL::Products'):'COMPLEX: raw uses M3 short codes (CORN/SB/SBM), Jayson uses TGQ-prefixed codes; needs code-map. Sheet also has seller banner rows.',
 ('Products','Account QL Feed::Products'):'COMPLEX: stub (6 rows); same code-system mismatch.',
 ('Ports','Shipping QLI & QLF::Ports'):'COMPLEX: Shipping port codes differ from Jayson port codes (70 raw vs 37 Jayson); match by name needed.',
 ('States','Account QL Feed::States'):'REVIEW: 196 matched; many ADDED are country-placeholder rows (no state name). Reference data.',
 ('Inventory Locations','Sales QLI & QLF::Inventory Locations_QLF_29.6.26'):'COMPLEX: Sales M3 Code collides with Jayson code (PK means different location); prefer Shipping source.',
 ('Inventory Locations','Sales QLI & QLF::Inventory Locations_QLI_29.6.26'):'COMPLEX: same code-collision issue as QLF.',
 ('Inventory Locations','Shipping QLI & QLF::Inventory Location'):'CLEAN: 32 matched on code; Shipping is the authoritative Inventory Location source.',
 ('Vendor','Purchasing QL Feed  QL::Vendor'):'Internal/Farms entities w/o M3 Code (blank key); compare by name needed for write-back.',
 ('Customer','Purchasing QL Feed  QL::Customer'):'Internal/Farms entities w/o M3 Code (blank key); compare by name needed for write-back.',
}
def status(e,s,r):
    n=NOTES.get((e,s),'')
    if n.startswith('COMPLEX'): return 'COMPLEX'
    if r['added']==0 and r['changed']==0: return 'IN SYNC'
    return 'HAS DIFFS'

sm=pd.read_csv(f"{OUT}/summary.csv")
sm['status']=[status(r['entity'],r['source'],r) for _,r in sm.iterrows()]
sm['note']=[NOTES.get((r['entity'],r['source']),'') for _,r in sm.iterrows()]
sm=sm[['entity','source','status','added','changed','matched','missing_in_raw','raw_rows','jayson_rows','raw_dupkeys','blankkey','note']]
det=pd.read_csv(f"{OUT}/discrepancies.csv").fillna('')

def write_tab(title, df, banner):
    meta=svc.spreadsheets().get(spreadsheetId=SID).execute()
    titles=[s['properties']['title'] for s in meta['sheets']]
    if title not in titles:
        svc.spreadsheets().batchUpdate(spreadsheetId=SID,
            body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
    svc.spreadsheets().values().clear(spreadsheetId=SID, range=f"'{title}'").execute()
    header=[list(map(str,df.columns))]
    body=[['' if pd.isna(v) else str(v) for v in row] for row in df.itertuples(index=False,name=None)]
    values=[[banner]]+[[]]+header+body
    svc.spreadsheets().values().update(spreadsheetId=SID, range=f"'{title}'!A1",
        valueInputOption='RAW', body={'values':values}).execute()
    print(f"wrote '{title}': {len(df)} rows")

write_tab('RECON 300626 - Summary', sm,
  'Read-only reconciliation of "300626 Master Data" Drive folder vs this sheet. Generated 2026-07-01. status: IN SYNC / HAS DIFFS / COMPLEX(needs code mapping). added=rows in raw not in Jayson(by key); changed=field differs(raw non-blank); missing_in_raw=Jayson keys this source did not cover. NO data tab was modified.')
write_tab('RECON 300626 - Details', det,
  'Per-row discrepancies (read-only). type=ADDED(new in raw) / CHANGED(field differs). raw_value vs jayson_value. Each row labelled by source file::sheet.')
