# -*- coding: utf-8 -*-
"""Standardize jayson spec-group names 'H-PRO' -> 'HI-PRO' (missing 'I') to match raw + the other
HI-PRO groups. Cascade across the 4 name-FK tabs: SpecGroup.name, Spec Group Spec.SpecGroupName2,
Spec Group x Product.spec_group, SpecGroupFIP.SpecGroupName. Backup + audit. (HI-PRO does NOT contain
the substring H-PRO, so the replace only hits the misspelled ones.)"""
import re, csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
PAT=re.compile(r'H-PRO(?=\s|$)')
TABS=[('SpecGroup','name'),('Spec Group Spec','SpecGroupName2'),('Spec Group x Product','spec_group'),('SpecGroupFIP','SpecGroupName')]
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def colA1(i):
    s=''; i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
total=0
for tab,col in TABS:
    v=get(tab)
    if not v: print(f"{tab}: (empty)"); continue
    h=[c.strip() for c in v[0]]
    if col not in h: print(f"{tab}: no '{col}' col"); continue
    ci=h.index(col)
    with open(f"{BK}/{tab}.pre-hpro.csv",'w',newline='') as f: csv.writer(f).writerows(v)
    ups=[]
    for ri,r in enumerate(v[1:],start=2):
        r=r+['']*(len(h)-len(r)); old=r[ci]
        if PAT.search(old):
            new=PAT.sub('HI-PRO', old)
            ups.append({'range':f"'{tab}'!{colA1(ci)}{ri}",'values':[[new]]})
    if ups: retry(lambda: svc.spreadsheets().values().batchUpdate(spreadsheetId=JAY,body={'valueInputOption':'RAW','data':ups}).execute())
    total+=len(ups); print(f"{tab}.{col}: {len(ups)} cell(s) H-PRO -> HI-PRO")
print(f"TOTAL {total} cells fixed (backups *.pre-hpro.csv)")
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['SPECGROUP H-PRO->HI-PRO 2026-07-02',f'{total} cells standardized across SpecGroup/Spec Group Spec/Spec Group x Product/SpecGroupFIP. DB re-migration pending tunnel.']]}).execute())
print("audited.")
