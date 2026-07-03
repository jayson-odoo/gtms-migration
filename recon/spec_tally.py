# -*- coding: utf-8 -*-
"""Content-level tally of raw SpecGroup (draft blocks) vs jayson SpecGroup + Spec Group Spec.
Raw is a draft keyed by generic product; jayson expands per origin/seller variant. So we compare
at the (product -> set of SpecNames) level: which specs are in raw but not jayson, and vice versa,
per product. READ-ONLY."""
import glob, re, time
import openpyxl
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','QLF & QLI','QLI & QLF','PURCHASING -','ALL SELLERS'))
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']),cache_discovery=False)
def getj(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])

# ---- raw: parse draft blocks -> per product: set of SpecNames ----
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,SN,VT,mn,mx=gi('SpecGroupName2'),gi('SpecGroupName3 (Origin)'),gi('SpecName'),gi('value_type'),gi('minimum'),gi('maximum')
raw_specs=defaultdict(set); raw_orig=defaultdict(set); curp=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row))
    p=row[P].strip()
    if p and not banner(p): curp=norm(p)
    if curp is None: continue
    o=row[O].strip()
    if o and not banner(o) and not o.startswith('('): raw_orig[nk(curp)].add(norm(o))
    sn=row[SN].strip()
    if sn and (row[VT].strip() or (mn>=0 and row[mn].strip()) or (mx>=0 and row[mx].strip())):
        raw_specs[nk(curp)].add(nk(sn))
raw_prod_disp={nk(k):k for k in [norm(x) for x in []]}  # placeholder
# rebuild display names
curp=None; disp={}
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p): disp[nk(norm(p))]=norm(p)
NOSPEC={'DMXPLUSMOLDINHIBITOR'}  # non-spec products
raw_specs={k:v for k,v in raw_specs.items() if v and not k.startswith('PMQ') and k not in NOSPEC}
print(f"RAW: {len(raw_specs)} products carry specs; total distinct (product,spec) pairs={sum(len(v) for v in raw_specs.values())}")

# ---- jayson: SpecGroup names + Spec Group Spec -> map each group to a raw product by token containment ----
jsg=getj('SpecGroup'); jh=[norm(x) for x in jsg[0]]; jni=jh.index('name')
groups=[r[jni].strip() for r in jsg[1:] if len(r)>jni and r[jni].strip()]
def match_product(groupname):
    gk=nk(groupname); best=None
    for pk in raw_specs:
        if pk and pk in gk and (best is None or len(pk)>len(best)): best=pk
    return best
gs=getj('Spec Group Spec'); gh=[norm(x) for x in gs[0]]
gni=next((i for i,x in enumerate(gh) if nk(x)=='SPECGROUPNAME2'),0); sni=next((i for i,x in enumerate(gh) if nk(x)=='SPECNAME'),1)
jay_specs=defaultdict(set); unmatched=set()
for row in gs[1:]:
    row=row+['']*(len(gh)-len(row)); grp=row[gni].strip(); sn=row[sni].strip()
    if not grp or not sn: continue
    pk=match_product(grp)
    if pk: jay_specs[pk].add(nk(sn))
    else: unmatched.add(grp)

# ---- tally ----
print(f"JAYSON: {len(groups)} spec groups, {len(gs)-1} spec lines; mapped to {len(jay_specs)} raw products")
allp=sorted(set(raw_specs)|set(jay_specs), key=lambda k: disp.get(k,k))
print(f"\n{'PRODUCT':34} {'raw':>4} {'jay':>4}  missing_in_jayson / extra_in_jayson")
nmiss=nextra=0
for pk in allp:
    rs=raw_specs.get(pk,set()); js=jay_specs.get(pk,set())
    miss=rs-js; extra=js-rs
    nmiss+=len(miss); nextra+=len(extra)
    flag='' if not miss and not extra else '  <-- CHECK'
    md=disp.get(pk,pk)[:33]
    mtxt=('MISS:'+','.join(sorted(miss))) if miss else ''
    etxt=('EXTRA:'+','.join(sorted(extra))) if extra else ''
    print(f"{md:34} {len(rs):>4} {len(js):>4}  {mtxt} {etxt}{flag}")
print(f"\nTOTAL specs in raw not in jayson={nmiss} | in jayson not in raw={nextra}")
print(f"products in raw but NO jayson group: {sorted(disp[k] for k in raw_specs if k not in jay_specs)}")
if unmatched: print(f"jayson groups not matched to any raw product ({len(unmatched)}): {sorted(unmatched)[:10]}")
