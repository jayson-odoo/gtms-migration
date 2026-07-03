# -*- coding: utf-8 -*-
"""READ-ONLY. Inspect the 2 flagged issues: (A) RAPESEED block 17 raw Profat rows incl basis cols +
how the current jayson RAPESEED group represents Profat; (B) DDGS: what product codes the CURRENT
Spec Group x Product junction uses for the DDGS old groups (so TGQDDGS can be remapped to real prods)."""
import glob, re, time
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

# ---- (A) raw block 17 Profat rows ----
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,SN,MN,MX,MB,XB=[gi(x) for x in ['SpecGroupName2','SpecName','minimum','maximum','minimum_basis','maximum_basis']]
print("cols idx P,SN,MN,MX,MB,XB=",P,SN,MN,MX,MB,XB)
# find the RAPESEED block (product contains RAPESEED)
blk=0; inblk=False
print("\n(A) RAW rows for RAPESEED MEAL block (all spec lines, incl basis):")
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p):
        inblk = 'RAPESEED' in p.upper()
    if inblk and SN>=0 and row[SN].strip():
        print(f"   SpecName='{row[SN]}' min='{row[MN]}' max='{row[MX]}' min_basis='{row[MB] if MB>=0 else '-'}' max_basis='{row[XB] if XB>=0 else '-'}'")

# current jayson RAPESEED group Profat rows
ssh,ssd=rows2dicts(getj('Spec Group Spec'))
print("\n(A) CURRENT 'Spec Group Spec' rows for groups whose name has RAPESEED, SpecName~Profat:")
for d in ssd:
    if 'RAPESEED' in d.get('SpecGroupName2','').upper() and 'PROFAT' in nk(d.get('SpecName','')):
        print(f"   grp='{d['SpecGroupName2'][:40]}' spec='{d['SpecName']}' min='{d.get('minimum')}' max='{d.get('maximum')}' minb='{d.get('minimum_basis')}' maxb='{d.get('maximum_basis')}'")

# ---- (B) DDGS junction codes currently used ----
sxh,sxd=rows2dicts(getj('Spec Group x Product'))
g2c=defaultdict(set)
for d in sxd:
    g=norm(d.get('spec_group','')); c=d.get('code','').strip()
    if g and c: g2c[g].add(c)
print("\n(B) CURRENT junction codes for DDGS-related old groups (name has DISTILLERS or DDG):")
codes_all=set()
for g,cs in sorted(g2c.items()):
    if 'DISTILLER' in g.upper() or 'DDG' in nk(g):
        print(f"   {g[:52]:52} -> {sorted(cs)}"); codes_all|=cs
print("   distinct DDGS-side codes in current junction:", sorted(codes_all))
# products list of DDG*
sph,pdd=rows2dicts(getj('Products'))
print("   Products codes starting TGQDD*:", sorted([d['code'] for d in pdd if d.get('code','').upper().startswith('TGQDD')]))
print("PROBE2 DONE (read-only).")
