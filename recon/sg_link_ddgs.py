# -*- coding: utf-8 -*-
"""Link the two HI-PRO DDGS spec groups (48% + 49%) to product TGQDDGSHP (desc=HI-PRO DISTILLERS
DRIED GRAIN WITH SOLUBLES) in Spec Group x Product. Both were unlinked. Backup + audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
CODE='TGQDDGSHP'
GROUPS=['HI-PRO DISTILLERS DRIED GRAIN WITH SOLUBLES','HI-PRO DISTILLERS DRIED GRAIN WITH SOLUBLES (49% PROTEIN)']
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
# guard: code exists, groups exist, links not already present
assert CODE in {r[0].strip() for r in get('Products')[1:] if r}, f"{CODE} not in Products"
sgnames={r[1].strip() for r in get('SpecGroup')[1:] if len(r)>1}
for gname in GROUPS: assert gname in sgnames, f"missing SpecGroup {gname!r}"
sp=get('Spec Group x Product'); h=[c.strip() for c in sp[0]]; gi=h.index('spec_group'); pi=h.index('code')
with open(f"{BK}/Spec Group x Product.pre-ddgslink.csv",'w',newline='') as f: csv.writer(f).writerows(sp)
existing={(r[gi].strip(),r[pi].strip()) for r in sp[1:] if len(r)>max(gi,pi)}
rows=[]
for gname in GROUPS:
    if (gname,CODE) in existing: print(f"   already linked: {gname} -> {CODE}"); continue
    d={'spec_group':gname,'code':CODE}; rows.append([d.get(c,'') for c in h])
    print(f"   + {gname} -> {CODE}")
if rows:
    retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'Spec Group x Product'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows}).execute())
print(f"linked {len(rows)} row(s) (backup Spec Group x Product.pre-ddgslink.csv)")
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['HI-PRO DDGS PRODUCT LINK 2026-07-02',f'linked 48%+49% HI-PRO DDGS groups -> {CODE}. FLAG: existing (IND) HI-PRO DDGS groups mis-linked to TGQDDG/TGQDDGW(=WHEAT DDGS). DB migration pending tunnel.']]}).execute())
print("audited.")
