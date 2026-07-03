# -*- coding: utf-8 -*-
"""SPECGROUP COLLAPSE 86->68 - sheet rebuild (steps 1-4). Regenerates SpecGroup / Spec Group Spec /
SpecGroupFIP / Spec Group x Product from the 68 raw blocks + user's 'recommended name' (tab
'VALIDATION SpecGroup Blocks'). Product-level description/sales_spec_group_description carried from
current SpecGroup by product-name match (curated overlay preserved). SpecName canonicalized to the
Specifications sheet (+1 known typo). FIP regenerated from soya protein grade. DRY-RUN default:
prints summary + writes review tab 'RECON SpecGroup Collapse 68', touches no live tab.
GTMS_APPLY=1 : backup the 4 live tabs then OVERWRITE them. No DB access."""
import os, glob, re, time, csv
from collections import defaultdict, Counter
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
D='/home/src/raw_master/300626'; BK='/home/src/recon/backup'
APPLY=os.environ.get('GTMS_APPLY')=='1'
TYPO={'SANDINHCIINSOLIBLE':'Sand in HCl insoluble'}   # raw typo -> canonical (memory 2026-07-02)
JUNC_REMAP={'TGQDDGS':['TGQDDG','TGQDDGW']}           # raw rollup code -> real DDGS products (not in Products sheet)
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def flt(s):
    try: return float(str(s).strip())
    except: return None
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

# ---------- recommended names ----------
vb=getj('VALIDATION SpecGroup Blocks'); vh=[c.strip() for c in vb[0]]; rci=vh.index('recommended name')
rec={int(r[0]):norm(r[rci]) for r in vb[1:] if r and r[0].strip().isdigit() and len(r)>rci}

# ---------- parse 68 blocks (ordered) ----------
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,SD,VU,VT,MN,MX,MB,XB,MC,GD=[gi(x) for x in ['SpecGroupName2','SpecGroupName3 (Origin)','SpecGroupName4 (Seller)',
    'SpecName','SpecDescription','value_unit','value_type','minimum','maximum','minimum_basis','maximum_basis','M3 Code','SpecGroupDescription']]
def _has21(s): return '2:1' in re.sub(r'\s*:\s*',':',str(s)) and 'RECIPROCAL' in str(s).upper()
blocks=[]; cur=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p):
        cur={'product':norm(p),'code':'','desc':'','specs':[],'has21':False}; blocks.append(cur)
    if cur is None: continue
    if any(_has21(c) for c in row): cur['has21']=True
    if MC>=0 and row[MC].strip() and not cur['code']: cur['code']=row[MC].strip()
    if GD>=0 and row[GD].strip() and not cur['desc']: cur['desc']=norm(row[GD])
    if SN>=0 and row[SN].strip() and ((MN>=0 and row[MN].strip()) or (MX>=0 and row[MX].strip())):
        cur['specs'].append(dict(name=norm(row[SN]),desc=norm(row[SD]) if SD>=0 else '',unit=row[VU].strip() if VU>=0 else '',
            vtype=row[VT].strip() if VT>=0 else '',mn=row[MN].strip() if MN>=0 else '',mx=row[MX].strip() if MX>=0 else '',
            mb=row[MB].strip() if MB>=0 else '',xb=row[XB].strip() if XB>=0 else ''))
assert len(blocks)==68, f"expected 68 blocks got {len(blocks)}"
assert all(rec.get(i) for i in range(1,69)), "missing recommended name"
names=[rec[i] for i in range(1,69)]
assert len(set(names))==68, f"duplicate recommended names: {[n for n,c in Counter(names).items() if c>1]}"

# ---------- Specifications canonical + typo ----------
sph,spd=rows2dicts(getj('Specifications'))
canon={nk(d['name']):d['name'].strip() for d in spd if d.get('name','').strip()}
def resolve_spec(sn):
    k=nk(sn)
    if k in canon: return canon[k], True
    if k in TYPO: return TYPO[k], True     # canonical exists?
    return sn, False

# ---------- product-level desc/sales carry from current SpecGroup ----------
sgh,sgd=rows2dicts(getj('SpecGroup'))
prods=sorted({b['product'] for b in blocks}, key=lambda p:-len(nk(p)))  # longest first
def match_product(gname):
    gk=nk(gname)
    for p in prods:                          # longest product that is a substring of the group name
        if nk(p) and nk(p) in gk: return p
    return None
prod_sales=defaultdict(Counter); prod_desc=defaultdict(Counter); unmatched_old=0
for d in sgd:
    gn=norm(d.get('name','')); p=match_product(gn)
    if not p: unmatched_old+=1; continue
    if d.get('sales_spec_group_description','').strip(): prod_sales[p][d['sales_spec_group_description'].strip()]+=1
    if d.get('description','').strip(): prod_desc[p][d['description'].strip()]+=1
def carry(counter,p): return counter[p].most_common(1)[0][0] if counter.get(p) else ''

# ---------- build the 4 tab payloads ----------
SG_H=['id','name','description','sales_spec_group_description','is_active']
SS_H=['SpecGroupName2','SpecName','SpecDescription','value_unit','value_type','minimum','maximum','minimum_basis','maximum_basis','is_derived']
FIP_H=['SpecGroupName','SpecName','minimum','maximum','fip']
SX_H=['spec_group','code']
FIPTPL={'46':[('46','46.5','1'),('45.5','46','2')],'47':[('47.5','48','1'),('47','47.5','2')]}
def fipgrade(mn_,mx_):
    a,b=flt(mn_),flt(mx_)
    if a is not None and abs(a-47)<0.01: return '47'
    if b is not None and abs(b-48)<0.01: return '47'
    if (a is not None and abs(a-45.5)<0.01) or (b is not None and abs(b-46.5)<0.01): return '46'
    return None

sg_rows=[]; ss_rows=[]; fip_rows=[]; sx_rows=[]
unresolved=Counter(); dup_specname=[]; sales_conflict=[]; desc_conflict=[]
code_not_in_products=[]
sph2,pdd=rows2dicts(getj('Products')); pcodes={d.get('code','').strip() for d in pdd if d.get('code','').strip()}
def fmtnum(x): return '' if x is None else (str(int(x)) if float(x).is_integer() else str(x))
def merge_specs(lst):   # collapse tiered dup-SpecName rows: floor of mins, ceil of maxes/bases
    mins=[flt(s['mn']) for s in lst if s['mn']!='' and flt(s['mn']) is not None]
    maxs=[flt(s['mx']) for s in lst if s['mx']!='' and flt(s['mx']) is not None]
    mbs =[flt(s['mb']) for s in lst if s['mb']!='' and flt(s['mb']) is not None]
    xbs =[flt(s['xb']) for s in lst if s['xb']!='' and flt(s['xb']) is not None]
    return dict(name=lst[0]['name'],desc=lst[0]['desc'],unit=lst[0]['unit'],vtype=lst[0]['vtype'],
        mn=fmtnum(min(mins) if mins else None),mx=fmtnum(max(maxs) if maxs else None),
        mb=fmtnum(max(mbs) if mbs else None),xb=fmtnum(max(xbs) if xbs else None))
for i in range(1,69):
    b=blocks[i-1]; nm=rec[i]
    d_desc=b['desc'] or carry(prod_desc,b['product'])          # raw per-block desc authoritative
    d_sales=carry(prod_sales,b['product'])                     # product-level sales overlay (not in raw)
    if len(prod_sales.get(b['product'],{}))>1: sales_conflict.append((i,b['product']))
    sg_rows.append(['', nm, d_desc, d_sales, 'TRUE'])
    # specs: group by canonical name (order-preserving), merge tiered duplicates
    grouped={}
    for sp in b['specs']:
        cn,ok=resolve_spec(sp['name'])
        if not ok: unresolved[sp['name']]+=1
        sp2=dict(sp); sp2['name']=cn
        grouped.setdefault(nk(cn),[]).append(sp2)
    for k,lst in grouped.items():
        if len(lst)>1 and {(s['mn'],s['mx']) for s in lst}!={(lst[0]['mn'],lst[0]['mx'])}:
            dup_specname.append((i,nm,lst[0]['name'],[(s['mn'],s['mx'],s['mb']) for s in lst]))
        m=merge_specs(lst)
        ss_rows.append([nm,m['name'],m['desc'] or m['name'],m['unit'],m['vtype'],m['mn'],m['mx'],m['mb'],m['xb'],'FALSE'])
    # FIP: only blocks whose spec text has "Non-Reciprocal Allowances 2:1" (the mixed 1:1 & 2:1 tier),
    # with a determinable protein grade (user's authoritative rule; see recon/fip_rebuild.py)
    if b['has21']:
        prot=next((sp for sp in b['specs'] if sp['name'].strip().lower()=='protein'),None)
        g=fipgrade(prot['mn'],prot['mx']) if prot else None
        if g:
            for lo,hi,fp in FIPTPL[g]: fip_rows.append([nm,'Protein',lo,hi,fp])
    # junction: block code -> real product code(s) (remap rollup codes not in Products)
    for code in JUNC_REMAP.get(b['code'],[b['code']]):
        sx_rows.append([nm,code])
        if code not in pcodes: code_not_in_products.append((i,nm,code))

# ---------- report ----------
print("="*70)
print(f"SPECGROUP COLLAPSE 86->68  |  MODE = {'*** APPLY (overwrite live tabs) ***' if APPLY else 'DRY-RUN'}")
print("="*70)
print(f"SpecGroup       : 86 -> {len(sg_rows)} rows")
print(f"Spec Group Spec : {len(ss_rows)} spec lines (was 802)")
print(f"SpecGroupFIP    : {len(fip_rows)} rows (was 48)  [{len(fip_rows)//2} soya groups x2]")
print(f"Spec Group x Product : {len(sx_rows)} rows (block code -> group; was 314 rows/80 pairs)")
print(f"\nold SpecGroup rows not matched to any block-product (no carry): {unmatched_old}")
print(f"UNRESOLVED SpecNames (after typo map): {dict(unresolved)}")
print(f"within-block DUPLICATE SpecName w/ different min/max (TIER COLLISION): {len(dup_specname)}")
for x in dup_specname: print("   TIER:",x)
print(f"blocks whose product has CONFLICTING sales_desc across old groups (took majority): {sales_conflict}")
print(f"blocks whose product has CONFLICTING description across old groups (took majority): {desc_conflict}")
print(f"junction codes NOT in Products sheet (won't resolve on migrate): {code_not_in_products}")
sg_no_sales=[rec[i] for i in range(1,69) if not sg_rows[i-1][3]]
print(f"new groups with BLANK sales_spec_group_description ({len(sg_no_sales)}): {[n[:30] for n in sg_no_sales]}")
print("\nSAMPLE new SpecGroup rows:")
for row in sg_rows[:4]+sg_rows[-2:]:
    print(f"   name='{row[1][:48]}' desc='{row[2][:22]}' sales='{row[3][:22]}'")

def overwrite(title, header, rows):
    v=getj(title)
    with open(f"{BK}/{title}.pre-collapse.csv",'w',newline='') as fh: csv.writer(fh).writerows(v)
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':[header]+rows}).execute())
    print(f"   OVERWROTE '{title}': {len(rows)} rows (backup {BK}/{title}.pre-collapse.csv)")

if APPLY:
    print("\n*** APPLYING (backup + overwrite 4 live tabs) ***")
    overwrite('SpecGroup', SG_H, sg_rows)
    overwrite('Spec Group Spec', SS_H, ss_rows)
    overwrite('SpecGroupFIP', FIP_H, fip_rows)
    overwrite('Spec Group x Product', SX_H, sx_rows)
    cur=getj('RECON 300626 - Applied')
    note=[['SPECGROUP COLLAPSE 86->68 (sheet rebuild)', f'SpecGroup {len(sg_rows)} / Spec {len(ss_rows)} / FIP {len(fip_rows)} / junction {len(sx_rows)}']]
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
    print("   audited to 'RECON 300626 - Applied'.")
else:
    title='RECON SpecGroup Collapse 68'
    meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=JAY).execute())
    if title not in [s['properties']['title'] for s in meta['sheets']]:
        retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
    review=[['#','new group name','description','sales_spec_group_description','n_specs','fip','code','code_in_products']]
    for i in range(1,69):
        b=blocks[i-1]; nfip=sum(1 for x in fip_rows if x[0]==rec[i])
        nsp=sum(1 for x in ss_rows if x[0]==rec[i])
        review.append([i,rec[i],sg_rows[i-1][2][:60],sg_rows[i-1][3][:60],nsp,nfip,b['code'],'Y' if b['code'] in pcodes else 'NO'])
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':review}).execute())
    print(f"\nDRY-RUN: wrote review tab '{title}' ({len(review)-1} groups). No live tab changed. Set GTMS_APPLY=1 to overwrite.")
