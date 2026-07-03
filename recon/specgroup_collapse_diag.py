# -*- coding: utf-8 -*-
"""READ-ONLY diagnostic for the SpecGroup 86->68 collapse. Re-parses raw blocks (same logic as
specgroup_collapse_plan), reads the user's 'VALIDATION SpecGroup Blocks' tab (recommended names),
reads current SpecGroup/Spec Group Spec/SpecGroupFIP/Spec Group x Product tabs, and reads prod DB
state (spec groups/details/fips/product junctions/contract_specifications). No writes."""
import os, glob, re, time, psycopg2
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def is_pack(o):
    u=str(o).upper(); return any(t in u for t in ('IN BULK','CONTAINER','20FT','40FT','RESERVED','DISABLED','GTMS'))
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])

# ---- 1. parse raw blocks (block_compare parsing: one block per non-banner SpecGroupName2 row) ----
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
print("RAW FILE:", f.split('/')[-1])
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,mn,mx=gi('SpecGroupName2'),gi('SpecGroupName3 (Origin)'),gi('SpecGroupName4 (Seller)'),gi('SpecName'),gi('minimum'),gi('maximum')
COL={'SpecName':gi('SpecName'),'minimum':gi('minimum'),'maximum':gi('maximum'),'value_unit':gi('value_unit'),
     'value_type':gi('value_type'),'minimum_basis':gi('minimum_basis'),'maximum_basis':gi('maximum_basis'),
     'M3 Code':gi('M3 Code'),'SpecGroupDescription':gi('SpecGroupDescription'),'SpecDescription':gi('SpecDescription')}
print("header cols found:", {k:v for k,v in COL.items()})
blocks=[]; cur=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p):
        cur={'product':norm(p),'origins':[],'sellers':[],'code':'','desc':'','specs':[]}; blocks.append(cur)
    if cur is None: continue
    if O>=0 and row[O].strip() and not banner(row[O]) and not row[O].strip().startswith('('): cur['origins'].append(norm(row[O]))
    if S>=0 and row[S].strip() and not banner(row[S]): cur['sellers'].append(norm(row[S]))
    if COL['M3 Code']>=0 and row[COL['M3 Code']].strip() and not cur['code']: cur['code']=row[COL['M3 Code']].strip()
    if COL['SpecGroupDescription']>=0 and row[COL['SpecGroupDescription']].strip() and not cur['desc']: cur['desc']=norm(row[COL['SpecGroupDescription']])
    if SN>=0 and row[SN].strip() and ((mn>=0 and row[mn].strip()) or (mx>=0 and row[mx].strip())):
        cur['specs'].append(norm(row[SN]))
print(f"\nRAW BLOCKS PARSED = {len(blocks)}")

# ---- 2. read user's recommended-name tab ----
vb=getj('VALIDATION SpecGroup Blocks')
hdr=[c.strip() for c in vb[0]]
print("\n'VALIDATION SpecGroup Blocks' header:", hdr)
# find recommended-name column
rc=next((i for i,c in enumerate(hdr) if 'recommend' in c.lower()),-1)
print("recommended-name col index:", rc)
recmap={}
if rc>=0:
    for row in vb[1:]:
        if not row or not row[0].strip().isdigit(): continue
        bnum=int(row[0]); nm=row[rc].strip() if len(row)>rc else ''
        recmap[bnum]=nm
print(f"recommended names filled: {sum(1 for v in recmap.values() if v)}/{len(recmap)} numbered rows")
# cross-check block product alignment vs tab
print("\nBLOCK ALIGNMENT (raw parse vs tab 'raw product') + recommended name:")
mismatch=0
for i,b in enumerate(blocks,1):
    tabrow=next((row for row in vb[1:] if row and row[0].strip()==str(i)),None)
    tabprod=tabrow[1].strip() if tabrow and len(tabrow)>1 else '<none>'
    ok='OK' if nk(tabprod)==nk(b['product']) else 'MISMATCH'
    if ok=='MISMATCH': mismatch+=1
    print(f"  blk {i:>2} [{ok}] raw={b['product'][:26]:26} tab={tabprod[:22]:22} O={','.join(b['origins'])[:24]:24} nspec={len(b['specs'])} -> REC='{recmap.get(i,'')[:40]}'")
print(f"\nblock/tab product mismatches = {mismatch}")
print(f"blocks with EMPTY recommended name = {[i for i in range(1,len(blocks)+1) if not recmap.get(i)]}")
# duplicate recommended names?
from collections import Counter
rc2=Counter(v for v in recmap.values() if v)
dups={k:c for k,c in rc2.items() if c>1}
print(f"DUPLICATE recommended names (same name for >1 block) = {dups}")

# ---- 3. current sheet tabs ----
print("\n=== CURRENT SHEET TABS ===")
for t in ['SpecGroup','Spec Group Spec','SpecGroupFIP','Spec Group x Product']:
    v=getj(t); vh=[c.strip() for c in v[0]] if v else []
    print(f"  '{t}': rows={len(v)-1 if v else 0} cols={vh}")

# ---- 4. DB state ----
if os.environ.get('DIAG_SKIP_DB')=='1':
    print("\n[DIAG_SKIP_DB=1 -> DB section skipped]"); raise SystemExit
print("\n=== PROD DB STATE ===")
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
for q,lbl in [("select count(*) from master_specification_groups","spec_groups"),
              ("select count(*) from master_specification_details","spec_details"),
              ("select count(*) from master_specification_fips","spec_fips"),
              ("select count(*) from product_specification_groups","product_spec_groups"),
              ("select count(*) from contract_specifications","contract_specifications")]:
    cur.execute(q); print(f"  {lbl} = {cur.fetchone()[0]}")
cur.execute("select id,name from master_specification_groups order by id")
dbg=cur.fetchall()
print(f"\n  DB spec groups ({len(dbg)}):")
for i,n in dbg: print(f"    id={i:>3} {n}")
# contract_specifications referencing which group ids
cur.execute("""select column_name from information_schema.columns where table_name='contract_specifications' order by ordinal_position""")
csc=[r[0] for r in cur.fetchall()]
print(f"\n  contract_specifications columns: {csc}")
gcol=next((x for x in csc if 'group' in x and 'id' in x),None)
if gcol:
    cur.execute(f"select {gcol}, count(*) from contract_specifications group by {gcol} order by {gcol}")
    print(f"  contract_specifications.{gcol} usage: {cur.fetchall()}")
c.close()
print("\nDIAG DONE (read-only).")
