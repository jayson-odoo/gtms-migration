# -*- coding: utf-8 -*-
"""READ-ONLY. User's rule: a spec group has the 2:1 FIP tier iff one of its spec rows' text contains
'Non-Reciprocal Allowances 2:1'. Scan the 68 raw SpecGroup blocks (all text cols) for that phrase and
report which blocks qualify + their protein grade -> proposed FIP rows. Also show the 1:1 variant count."""
import glob, re
import openpyxl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
D='/home/src/raw_master/300626'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def flt(s):
    try: return float(str(s).strip())
    except: return None
def has21(s): return '2:1' in re.sub(r'\s*:\s*',':',str(s)) and 'RECIPROCAL' in str(s).upper()
def has11(s): return '1:1' in re.sub(r'\s*:\s*',':',str(s)) and 'RECIPROCAL' in str(s).upper()
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]; wb.close()
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,SN,MN,MX=gi('SpecGroupName2'),gi('SpecName'),gi('minimum'),gi('maximum')
# recommended names
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
vb=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'VALIDATION SpecGroup Blocks'").execute().get('values',[])
vh=[c.strip() for c in vb[0]]; rc=vh.index('recommended name')
rec={int(x[0]):x[rc].strip() for x in vb[1:] if x and x[0].strip().isdigit() and len(x)>rc}
blocks=[]; cur=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p): cur={'has21':False,'has11':False,'protein':None,'hits':[]}; blocks.append(cur)
    if cur is None: continue
    for cellv in row:
        if has21(cellv): cur['has21']=True; cur['hits'].append(norm(cellv)[:60])
        if has11(cellv): cur['has11']=True
    if SN>=0 and row[SN].strip().lower()=='protein' and cur['protein'] is None and (row[MN].strip() or row[MX].strip()):
        cur['protein']=(row[MN].strip(),row[MX].strip())
def grade(pr):
    if not pr: return None
    a,b=flt(pr[0]),flt(pr[1])
    if a is not None and abs(a-47)<.01: return '47'
    if b is not None and abs(b-48)<.01: return '47'
    if (a is not None and abs(a-45.5)<.01) or (b is not None and abs(b-46.5)<.01): return '46'
    return None
q21=[i for i,b in enumerate(blocks,1) if b['has21']]
print(f"blocks total={len(blocks)} | with 'Non-Reciprocal Allowances 2:1' = {len(q21)} | with '...1:1' = {sum(1 for b in blocks if b['has11'])}")
print("\nBLOCKS WITH 2:1 (FIP-eligible):")
nrows=0
for i in q21:
    b=blocks[i-1]; g=grade(b['protein'])
    fip = 2 if g else 0; nrows+=fip
    print(f"  blk {i:>2} grade={g} protein={b['protein']} '{rec.get(i,'')[:52]}'")
    print(f"        hit: {b['hits'][0] if b['hits'] else ''}")
print(f"\n=> {len(q21)} FIP groups, {nrows} FIP rows (2 per graded group)")
