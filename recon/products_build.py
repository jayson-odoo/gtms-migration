# -*- coding: utf-8 -*-
import re, csv, time, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'; PUR='Purchasing QL Feed  QL International - QL Master Data (Part 1) 20260629.xlsx'; BK='/home/src/recon/backup'
def n(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
# marked product codes from PSC tab
psc=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'RECON 300626 - PSC Candidates'").execute()).get('values',[])
marked=set()
for r in psc:
    if len(r)>0 and str(r[0]).strip().upper().startswith('Y'):
        _c=next((str(c).strip().upper() for c in r if str(c).strip().upper().startswith('TGQ')), None)
        if _c: marked.add(_c)
print("marked product codes:", sorted(marked))
# batch read Jayson refs
bg=retry(lambda: svc.spreadsheets().values().batchGet(spreadsheetId=SID, ranges=["'Products'","'Packing Unit'","'UoM'"]).execute())['valueRanges']
def rows(vr): 
    v=vr.get('values',[]); h=v[0]; return h,[dict(zip(h,r)) for r in v[1:]]
ph,pj=rows(bg[0]); kh,kj=rows(bg[1]); uh,uj=rows(bg[2])
existing=set(n(d.get('code','')) for d in pj)
pumap={}
for d in kj:
    for f in ('code','original_code','description'):
        if d.get(f): pumap[n(d[f])]=d.get('code','')
umap={}
for d in uj:
    for f in ('code','description'):
        if d.get(f): umap[n(d[f])]=d.get('code','')
# raw products
rp=pd.read_excel(f"{DIR}/{PUR}",sheet_name='Products',header=0,dtype=str).fillna('')
rp['k']=rp['M3 Code'].map(n)
built=[]; skip_exist=[]; unresolved=[]
seen=set()
for _,r in rp.iterrows():
    k=r['k']
    if k not in marked or k in seen: continue
    seen.add(k)
    if k in existing: skip_exist.append(r['M3 Code']); continue
    desc=str(r['description']).strip()
    pu=pumap.get(n(r.get('packing_unit','')),'')
    uom=umap.get(n(r.get('default_uom','')),'')
    act='FALSE' if 'NOT IN USE' in desc.upper() else 'TRUE'
    row=dict(code=str(r['M3 Code']).strip(), contract_number_reference=str(r.get('contract_number_reference','')).strip(),
             description=desc, **{'GTMS Packing Unit':pu}, default_uom=uom, hs_code=str(r.get('hs_code','')).strip(), is_active=act)
    if not pu or not uom: unresolved.append((r['M3 Code'], f"packing='{r.get('packing_unit','')}'->{pu or '?'} uom='{r.get('default_uom','')}'->{uom or '?'}"))
    built.append(row)
print(f"\nmarked found in raw={len(seen)} | already in Jayson(skip)={len(skip_exist)} {skip_exist} | to-build={len(built)}")
print(f"UNRESOLVED packing/uom ({len(unresolved)}):")
for c,m in unresolved: print("   ",c,m)
print("\nBUILD preview:")
for b in built: print(f"   {b['code']:10} act={b['is_active']:5} pu={b['GTMS Packing Unit']:6} uom={b['default_uom']:5} {b['description'][:38]}")
# write staging (do NOT append yet - packing/uom needs confirming)
title='RECON 300626 - Products NEW'
meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=SID).execute())
if title not in [s['properties']['title'] for s in meta['sheets']]:
    retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=SID,range=f"'{title}'").execute())
cols=['code','contract_number_reference','description','GTMS Packing Unit','default_uom','hs_code','is_active']
vals=[['STAGING: new products (packing/uom FK-mapped). ? = unresolved, fix before go-live.'],[],cols]+[[b[c] for c in cols] for b in built]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':vals}).execute())
print(f"\nwrote staging '{title}' ({len(built)} rows)")
