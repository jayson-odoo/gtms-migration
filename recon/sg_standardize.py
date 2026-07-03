# -*- coding: utf-8 -*-
"""Standardize spec-group market prefix -> parenthesized (IND)/(VN) across SpecGroup, Spec Group Spec,
Spec Group x Product, SpecGroupFIP. Backup + audit. Sheet-only (migration + cleanup follow)."""
import re, csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def std(name):
    n=name
    if '(IND)' not in n: n=re.sub(r'\bIND\b','(IND)',n)
    if '(VN)' not in n: n=re.sub(r'\bVN\b','(VN)',n)
    return n
# build rename map from SpecGroup names
sg=get('SpecGroup'); gh=[x.strip() for x in sg[0]]; ni=gh.index('name')
rmap={}
for r in sg[1:]:
    nm=r[ni].strip() if len(r)>ni else ''
    if nm:
        nn=std(nm)
        if nn!=nm: rmap[nm]=nn
print(f"groups to rename = {len(rmap)}")
for o,n in rmap.items(): print(f"   {o}  ->  {n}")
# collision check: new name already an existing (unchanged) group?
existing={r[ni].strip() for r in sg[1:] if len(r)>ni and r[ni].strip()}
coll=[n for n in rmap.values() if n in existing and n not in rmap]
print("collisions (new name already exists):", coll if coll else "none")
assert not coll, "abort: rename would collide"
# apply to each tab/col
def apply_tab(tab, col, bkname):
    v=get(tab); h=[x.strip() for x in v[0]]; ci=h.index(col)
    with open(f"{BK}/{bkname}",'w',newline='') as f: csv.writer(f).writerows(v)
    n=0; rows=[h]
    for r in v[1:]:
        r=r+['']*(len(h)-len(r)); cur=r[ci].strip()
        if cur in rmap: r[ci]=rmap[cur]; n+=1
        else:
            nn=std(cur)   # also fix any name not in SpecGroup map (defensive)
            if nn!=cur and cur: r[ci]=nn; n+=1
        rows.append(r[:len(h)])
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{tab}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{tab}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
    print(f"   {tab}: {n} cells renamed")
apply_tab('SpecGroup','name','SpecGroup.pre-std.csv')
apply_tab('Spec Group Spec','SpecGroupName2','Spec Group Spec.pre-std.csv')
apply_tab('Spec Group x Product','spec_group','Spec Group x Product.pre-std.csv')
apply_tab('SpecGroupFIP','SpecGroupName','SpecGroupFIP.pre-std.csv')
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 5 SpecGroup name standardize (IND)/(VN) 2026-07-01',f'{len(rmap)} groups renamed across 4 tabs']]}).execute())
print("audited.")
