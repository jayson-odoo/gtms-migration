# -*- coding: utf-8 -*-
"""READ-ONLY. Dump the sheet mappings needed to design the 86->68 collapse safely:
current SpecGroup(name->sales_desc), Spec Group x Product cardinality (group->codes, code->groups),
SpecGroupFIP rows, raw block codes + validate against Products sheet. No prod, no writes."""
import glob, re, time
from collections import defaultdict, Counter
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def rows2dicts(v):
    h=[c.strip() for c in v[0]]; return h,[dict(zip(h,r+['']*(len(h)-len(r)))) for r in v[1:]]

# raw blocks with codes
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,SN,mn,mx,MC=gi('SpecGroupName2'),gi('SpecGroupName3 (Origin)'),gi('SpecName'),gi('minimum'),gi('maximum'),gi('M3 Code')
blocks=[]; cur=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p): cur={'product':norm(p),'code':'','codes':set(),'nspec':0}; blocks.append(cur)
    if cur is None: continue
    if MC>=0 and row[MC].strip():
        cur['codes'].add(row[MC].strip())
        if not cur['code']: cur['code']=row[MC].strip()
    if SN>=0 and row[SN].strip() and ((mn>=0 and row[mn].strip()) or (mx>=0 and row[mx].strip())): cur['nspec']+=1
print(f"raw blocks={len(blocks)}")
print("blocks with >1 distinct M3 Code:", [(i+1,b['product'],sorted(b['codes'])) for i,b in enumerate(blocks) if len(b['codes'])>1])
print("blocks with NO M3 Code:", [(i+1,b['product']) for i,b in enumerate(blocks) if not b['codes']])

# Products sheet codes
try:
    pv=getj('Products'); ph,pds=rows2dicts(pv)
    pcodes={d.get('code','').strip() for d in pds if d.get('code','').strip()}
    print(f"\nProducts sheet: {len(pcodes)} codes. header={ph[:6]}...")
except Exception as e:
    pcodes=set(); print("Products read err:",e)
blkcodes={c for b in blocks for c in b['codes']}
print("block codes NOT in Products sheet:", sorted(blkcodes-pcodes))

# current SpecGroup name -> sales_desc
sgv=getj('SpecGroup'); sgh,sgd=rows2dicts(sgv)
print(f"\ncurrent SpecGroup rows={len(sgd)} cols={sgh}")
salesdesc={norm(d['name']):d.get('sales_spec_group_description','').strip() for d in sgd}
n_sales=sum(1 for v in salesdesc.values() if v)
print(f"groups with non-blank sales_spec_group_description = {n_sales}")

# Spec Group x Product cardinality
sxv=getj('Spec Group x Product'); sxh,sxd=rows2dicts(sxv)
g2c=defaultdict(set); c2g=defaultdict(set)
for d in sxd:
    g=norm(d.get('spec_group','')); c=d.get('code','').strip()
    if g and c: g2c[g].add(c); c2g[c].add(g)
print(f"\nSpec Group x Product: {len(sxd)} rows | distinct groups={len(g2c)} | distinct codes={len(c2g)}")
card=Counter(len(v) for v in g2c.values())
print(f"  codes-per-group distribution (n_codes:count): {dict(sorted(card.items()))}")
print(f"  groups linking to >1 code (sample 15):")
for g,cs in list(sorted(g2c.items(), key=lambda kv:-len(kv[1])))[:15]:
    print(f"    {g[:50]:50} -> {len(cs)} codes: {sorted(cs)[:8]}")
# do old group names embed their product, so a group maps to 1 product logically but many SKU codes?
print(f"\n  codes-per-group where group name has a single product (map to see if multi-code = product SKUs):")

# SpecGroupFIP
fv=getj('SpecGroupFIP'); fh,fd=rows2dicts(fv)
print(f"\nSpecGroupFIP rows={len(fd)} cols={fh}")
fipgroups=Counter(norm(d.get('SpecGroupName','')) for d in fd)
print(f"  distinct FIP groups={len(fipgroups)}; rows per group={dict(Counter(fipgroups.values()))}")
for g,c in list(fipgroups.items())[:60]: print(f"    FIP: {g[:60]:60} x{c}")
print("\nDUMP DONE (read-only).")
