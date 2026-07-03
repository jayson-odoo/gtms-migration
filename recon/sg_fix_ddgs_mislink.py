# -*- coding: utf-8 -*-
"""Re-point mis-linked HI-PRO DISTILLERS spec groups: any (HI-PRO DISTILLER* group, TGQDDG|TGQDDGW)
-> TGQDDGSHP (the actual HI-PRO DDGS product). Full-tab rewrite w/ dedup. Backup + audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
BAD={'TGQDDG','TGQDDGW'}; GOOD='TGQDDGSHP'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
sp=get('Spec Group x Product'); h=[c.strip() for c in sp[0]]; gi=h.index('spec_group'); pi=h.index('code')
with open(f"{BK}/Spec Group x Product.pre-ddgsmislink.csv",'w',newline='') as f: csv.writer(f).writerows(sp)
out=[h]; seen=set(); fixed=0
for r in sp[1:]:
    r=r+['']*(len(h)-len(r)); grp=r[gi].strip(); code=r[pi].strip()
    if 'HI-PRO DISTILLER' in grp.upper() and code in BAD:
        code=GOOD; fixed+=1
    key=(grp,code)
    if key in seen: continue     # dedup (repointed rows may collide)
    seen.add(key); rr=r[:]; rr[pi]=code; out.append(rr)
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range="'Spec Group x Product'").execute())
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'Spec Group x Product'!A1",valueInputOption='RAW',body={'values':out}).execute())
print(f"re-pointed {fixed} HI-PRO DISTILLER links to {GOOD}; rows {len(sp)-1} -> {len(out)-1} (dedup)")
# verify HI-PRO DDGS group links now
final={(r[gi].strip(),r[pi].strip()) for r in out[1:]}
for g in ['HI-PRO DISTILLERS DRIED GRAIN WITH SOLUBLES','HI-PRO DISTILLERS DRIED GRAIN WITH SOLUBLES (49% PROTEIN)']:
    print(f"   {g[:50]:50} -> {sorted(c for gg,c in final if gg==g)}")
for g in sorted({gg for gg,c in final if 'HI-PRO DISTILLER' in gg.upper()}):
    print(f"   {g[:55]:55} -> {sorted(c for gg,c in final if gg==g)}")
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['HI-PRO DDGS MISLINK FIX 2026-07-02',f'{fixed} (IND) HI-PRO DISTILLERS links re-pointed TGQDDG/TGQDDGW -> {GOOD}']]}).execute())
print("audited.")
