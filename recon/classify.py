# -*- coding: utf-8 -*-
"""Classify each discrepancy into apply-safety buckets and emit a ChangePlan.
LIVE pass-1 entities only (tabs that directly feed prod pipelines). Picks one
authoritative source per entity to avoid Account/Purchasing double-writes."""
import re, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
OUT='/home/src/recon/out'

# authoritative source substring per entity (others dropped from plan)
AUTH={'Legal Entity':'Account','Tax':'Account QL Feed','Profit Centers':'Account QL Feed',
      'Trader (Salesperson)':'Account','Payment Term':'Account','Packing Unit':'Purchasing',
      'Countries':'Account QL Feed','UoM':'Account QL Feed','Users':'GTMS','States':'Account QL Feed'}
LIVE=set(AUTH)

def is_banner(k):
    k=str(k)
    if len(k)>24: return True
    if k.count(' ')>=3: return True
    if any(w in k.upper() for w in ['SDN BHD','PURCHASE CONTRACT','PURCHASING','SELLER','QL FEED','QL INTERNATIONAL']): return True
    return False

def classify(t, field, rv, jv):
    rv=str(rv).strip(); jv=str(jv).strip()
    if t=='ADDED':
        return 'ADD'
    if jv=='' or jv.lower()=='nan':
        return 'FILL_BLANK'
    a=re.sub(r'\s+',' ',rv).casefold(); b=re.sub(r'\s+',' ',jv).casefold()
    if b in a and len(a)>len(b): return 'RAW_RICHER'
    if a in b and len(b)>len(a): return 'JAYSON_RICHER'
    if len(a)>=len(b)*1.25: return 'RAW_RICHER'
    if len(b)>=len(a)*1.25: return 'JAYSON_RICHER'
    return 'CONFLICT'

det=pd.read_csv(f"{OUT}/discrepancies.csv").fillna('')
rows=[]
for _,r in det.iterrows():
    e=r['entity']
    if e not in LIVE: continue
    if AUTH[e] not in r['source']: continue
    cls=classify(r['type'], r['field'], r['raw_value'], r['jayson_value'])
    rec=''
    if r['type']=='ADDED':
        rec='HOLD-banner' if is_banner(r['key']) else 'REVIEW-add'
    else:
        rec={'FILL_BLANK':'APPLY','RAW_RICHER':'APPLY','JAYSON_RICHER':'HOLD-keep-jayson',
             'CONFLICT':'REVIEW'}[cls]
    rows.append([e,r['key'],r['name'],r['type'],r['field'],r['raw_value'],r['jayson_value'],cls,rec])
cp=pd.DataFrame(rows, columns=['entity','key','name','type','field','raw_value','jayson_value','class','recommend'])
cp.to_csv(f"{OUT}/changeplan.csv", index=False)
print("By recommendation:")
print(cp['recommend'].value_counts().to_string())
print("\nBy entity x recommend:")
print(cp.groupby(['entity','recommend']).size().to_string())
print("\n--- APPLY set (field updates) ---")
ap=cp[cp.recommend=='APPLY']
for _,r in ap.iterrows():
    print(f"  {r['entity']:18} {r['key']:8} {r['field']:24} '{str(r['raw_value'])[:40]}'  (was '{str(r['jayson_value'])[:30]}')")
print(f"\nAPPLY total: {len(ap)} | REVIEW-add: {sum(cp.recommend=='REVIEW-add')} | HOLD-banner: {sum(cp.recommend=='HOLD-banner')} | HOLD-keep-jayson: {sum(cp.recommend=='HOLD-keep-jayson')} | REVIEW: {sum(cp.recommend=='REVIEW')}")

# write ChangePlan tab
creds=Credentials.from_service_account_file(KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc=build('sheets','v4',credentials=creds,cache_discovery=False)
title='RECON 300626 - ChangePlan'
meta=svc.spreadsheets().get(spreadsheetId=SID).execute()
if title not in [s['properties']['title'] for s in meta['sheets']]:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
svc.spreadsheets().values().clear(spreadsheetId=SID, range=f"'{title}'").execute()
banner='Classified change plan for LIVE pass-1 entities (tabs that feed prod). recommend=APPLY(safe: raw fills blank or is richer) / REVIEW-add(new row, confirm) / HOLD-banner(sheet banner row, skip) / HOLD-keep-jayson(Jayson already better) / REVIEW(genuine value conflict). NOTHING applied yet.'
vals=[[banner],[]]+[list(cp.columns)]+[['' if pd.isna(v) else str(v) for v in row] for row in cp.itertuples(index=False,name=None)]
svc.spreadsheets().values().update(spreadsheetId=SID, range=f"'{title}'!A1", valueInputOption='RAW', body={'values':vals}).execute()
print(f"\nwrote '{title}': {len(cp)} rows")
