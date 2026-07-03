# -*- coding: utf-8 -*-
"""READ-ONLY. Read the LIVE Drive source SpecGroupFIP tab (file 1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa) via
Sheets API and enumerate every fip=2 row with its full inherited group identity (SpecGroupName2/product,
origin, seller) so we can map the genuine FIP groups to the 68 recommended-name blocks. No writes."""
import re, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
SRC='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'; GID=999784270
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def marker(o):
    u=str(o).upper(); return o.startswith('(') or any(t in u for t in ('IN BULK','CONTAINER','20FT','40FT','RESERVED','DISABLED','GTMS','BULK'))
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(20); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']),cache_discovery=False)
try:
    meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=SRC).execute())
except HttpError as e:
    print("CANNOT ACCESS SOURCE via Sheets API (maybe not shared w/ service account or is xlsx):", e); raise SystemExit
tab=next((s['properties']['title'] for s in meta['sheets'] if s['properties']['sheetId']==GID), None)
print("source file:", meta['properties']['title'])
print(f"tab for gid {GID}:", tab)
print("all tabs:", [(s['properties']['title'],s['properties']['sheetId']) for s in meta['sheets']])
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SRC,range=f"'{tab}'").execute()).get('values',[])
h=[norm(x) for x in v[0]]
print("\nheader:", h)
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,MN,MX,FMN,FMX,FP=[gi(x) for x in ['SpecGroupName2','SpecGroupName3 (Origin)','SpecGroupName4 (Seller)','SpecName','minimum','maximum','FIPminimum','FIPmaximum','FIP']]
if P<0: P=gi('SpecGroupName')
prod=''; real_o=''; seller=''; f2=[]; allfip=0
for r in v[1:]:
    r=[norm(x) for x in r]+['']*(len(h)-len(r))
    if P>=0 and r[P].strip() and not banner(r[P]): prod=r[P]; real_o=''; seller=''
    if O>=0 and r[O].strip() and not marker(r[O]) and not banner(r[O]): real_o=r[O]
    if S>=0 and r[S].strip() and not banner(r[S]): seller=r[S]
    fv=r[FP].strip() if FP>=0 else ''
    if fv in ('1.0','2.0','1','2'): allfip+=1
    if fv in ('2.0','2'):
        f2.append(dict(prod=prod,origin=real_o,seller=seller,spec=r[SN] if SN>=0 else '',
            mn=r[MN] if MN>=0 else '',mx=r[MX] if MX>=0 else '',fmn=r[FMN] if FMN>=0 else '',fmx=r[FMX] if FMX>=0 else ''))
print(f"\nLIVE source total fip rows={allfip} | fip=2 rows={len(f2)}")
print("\n=== fip=2 rows (product | REAL origin | seller | spec | band | FIP band) ===")
for e in f2:
    print(f"   {e['prod'][:24]:24} | {e['origin'][:22]:22} | {e['seller'][:26]:26} | {e['spec'][:8]:8} {e['mn']}-{e['mx']} FIP {e['fmn']}-{e['fmx']}")
