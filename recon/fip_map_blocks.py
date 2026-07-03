# -*- coding: utf-8 -*-
"""READ-ONLY. For each of the 12 raw fip=2 rows, resolve its REAL origin/seller (walk up past
(WM)/(EM)/IN BULK/packing markers) + grade, then match to the 68 SpecGroup recommended-name blocks
so we know exactly which 12 blocks should keep FIP."""
import glob, re
from collections import defaultdict
import openpyxl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
D='/home/src/raw_master/300626'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def marker(o):
    u=str(o).upper()
    return o.startswith('(') or any(t in u for t in ('IN BULK','CONTAINER','20FT','40FT','RESERVED','DISABLED','GTMS','BULK'))
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroupFIP']
rows=[[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]; wb.close()
h=[norm(x) for x in rows[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,MN,MX,FP=[gi(x) for x in ['SpecGroupName','SpecGroupName3 (Origin)','SpecGroupName4 (Seller)','SpecName','minimum','maximum','FIP']]
prod=''; real_o=''; seller=''; f2=[]
for r in rows[1:]:
    r=r+['']*(len(h)-len(r))
    if r[P].strip() and not banner(r[P]): prod=norm(r[P]); real_o=''; seller=''
    if O>=0 and r[O].strip() and not marker(r[O]) and not banner(r[O]): real_o=norm(r[O])
    if S>=0 and r[S].strip() and not banner(r[S]): seller=norm(r[S])
    if r[FP].strip() in ('2.0','2'):
        g='47' if (r[MN].strip().startswith('47')) else ('46' if r[MN].strip().startswith('45') else '?')
        f2.append(dict(prod=prod,origin=real_o,seller=seller,grade=g))
print(f"12 fip=2 rows with resolved real origin/seller/grade:")
grp=defaultdict(int)
for e in f2:
    print(f"   {e['prod'][:22]:22} O={e['origin'][:20]:20} S={e['seller'][:26]:26} grade={e['grade']}")
    grp[(nk(e['prod']),nk(e['origin']),nk(e['seller']),e['grade'])]+=1
print(f"\ndistinct (product,origin,seller,grade) FIP groups = {len(grp)}:")
for k,c in grp.items(): print(f"   prod={k[0][:18]:18} origin={k[1][:16]:16} seller={k[2][:20]:20} grade={k[3]} x{c}")

# match to the 68 recommended-name blocks (which currently got FIP in my regen)
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
vb=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'VALIDATION SpecGroup Blocks'").execute().get('values',[])
vh=[c.strip() for c in vb[0]]; rc=vh.index('recommended name')
print("\ncurrent recommended-name soya blocks (my regen gave FIP to graded ones):")
for r in vb[1:]:
    if not r or not r[0].strip().isdigit(): continue
    nm=r[rc] if len(r)>rc else ''
    if 'SOYA' in nm.upper(): print(f"   blk {r[0]:>2} '{nm[:60]}'")
