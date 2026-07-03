# -*- coding: utf-8 -*-
"""Rebuild SpecGroupFIP to the CORRECT set: FIP only for blocks whose spec text contains
'Non-Reciprocal Allowances 2:1' (user's authoritative rule). 2 rows per graded block (grade 46 ->
46-46.5/45.5-46 ; grade 47 -> 47.5-48/47-47.5). Backs up current tab, overwrites with 24 rows.
GTMS_APPLY=1 to write (else dry-run). Sheet-only, no DB."""
import os, re, glob, csv, time
import openpyxl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
D='/home/src/raw_master/300626'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; BK='/home/src/recon/backup'
APPLY=os.environ.get('GTMS_APPLY')=='1'
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def flt(s):
    try: return float(str(s).strip())
    except: return None
def has21(s): return '2:1' in re.sub(r'\s*:\s*',':',str(s)) and 'RECIPROCAL' in str(s).upper()
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(20); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
vb=getj('VALIDATION SpecGroup Blocks'); vh=[c.strip() for c in vb[0]]; rc=vh.index('recommended name')
rec={int(x[0]):norm(x[rc]) for x in vb[1:] if x and x[0].strip().isdigit() and len(x)>rc}
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]; wb.close()
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,SN,MN,MX=gi('SpecGroupName2'),gi('SpecName'),gi('minimum'),gi('maximum')
blocks=[]; cur=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p): cur={'has21':False,'protein':None}; blocks.append(cur)
    if cur is None: continue
    if any(has21(c) for c in row): cur['has21']=True
    if SN>=0 and row[SN].strip().lower()=='protein' and cur['protein'] is None and (row[MN].strip() or row[MX].strip()):
        cur['protein']=(row[MN].strip(),row[MX].strip())
TPL={'46':[('46','46.5','1'),('45.5','46','2')],'47':[('47.5','48','1'),('47','47.5','2')]}
def grade(pr):
    if not pr: return None
    a,b=flt(pr[0]),flt(pr[1])
    if a is not None and abs(a-47)<.01: return '47'
    if b is not None and abs(b-48)<.01: return '47'
    if (a is not None and abs(a-45.5)<.01) or (b is not None and abs(b-46.5)<.01): return '46'
    return None
fip_rows=[]; used=[]; skipped_nograde=[]
for i in range(1,69):
    b=blocks[i-1]
    if not b['has21']: continue
    g=grade(b['protein'])
    if not g: skipped_nograde.append(i); continue
    for lo,hi,fp in TPL[g]: fip_rows.append([rec[i],'Protein',lo,hi,fp])
    used.append((i,g,rec[i]))
print(f"MODE={'*** APPLY ***' if APPLY else 'DRY-RUN'}")
print(f"blocks with 2:1 = {sum(1 for b in blocks if b['has21'])} | FIP groups (graded) = {len(used)} | FIP rows = {len(fip_rows)}")
for i,g,nm in used: print(f"   blk {i:>2} grade={g} {nm[:56]}")
if skipped_nograde: print("  skipped (2:1 but no grade):", skipped_nograde)
H=['SpecGroupName','SpecName','minimum','maximum','fip']
if APPLY:
    cur_v=getj('SpecGroupFIP')
    with open(f"{BK}/SpecGroupFIP.pre-rulefix.csv","w",newline='') as fh: csv.writer(fh).writerows(cur_v)
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range="'SpecGroupFIP'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'SpecGroupFIP'!A1",valueInputOption='RAW',body={'values':[H]+fip_rows}).execute())
    print(f"OVERWROTE 'SpecGroupFIP': {len(fip_rows)} rows (backup {BK}/SpecGroupFIP.pre-rulefix.csv, was {len(cur_v)-1})")
else:
    print("DRY-RUN. GTMS_APPLY=1 to write.")
