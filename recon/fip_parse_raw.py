# -*- coding: utf-8 -*-
"""READ-ONLY. Parse raw 'SpecGroupFIP' tab as hierarchical blocks and extract the GENUINE FIP tiers:
a spec qualifies for FIP only if it has a FIP=2 row (mixed 1:1 & 2:1). Emit each qualifying spec with
its fip1 + fip2 bands (FIPminimum/FIPmaximum) and full block context (product/origin/seller/protein)."""
import glob, re
from collections import defaultdict
import openpyxl
D='/home/src/raw_master/300626'
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroupFIP']
rows=[[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]; wb.close()
h=[norm(x) for x in rows[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,MN,MX,FMN,FMX,FP=[gi(x) for x in ['SpecGroupName','SpecGroupName3 (Origin)','SpecGroupName4 (Seller)','SpecName','minimum','maximum','FIPminimum','FIPmaximum','FIP']]
blocks=[]; cur=None
for r in rows[1:]:
    r=r+['']*(len(h)-len(r)); p=r[P].strip()
    if p and not banner(p):
        cur={'product':norm(p),'origins':set(),'sellers':set(),'protein':None,'fips':defaultdict(dict)}; blocks.append(cur)
    if cur is None: continue
    if O>=0 and r[O].strip() and not banner(r[O]) and not r[O].strip().startswith('('): cur['origins'].add(norm(r[O]))
    if S>=0 and r[S].strip() and not banner(r[S]): cur['sellers'].add(norm(r[S]))
    sn=r[SN].strip() if SN>=0 else ''
    if sn.lower()=='protein' and cur['protein'] is None and (r[MN].strip() or r[MX].strip()):
        cur['protein']=(r[MN].strip(),r[MX].strip())
    fv=r[FP].strip() if FP>=0 else ''
    if fv in ('1.0','2.0','1','2') and sn:
        tier='1' if fv in ('1.0','1') else '2'
        cur['fips'][norm(sn)][tier]=(r[FMN].strip() if FMN>=0 else '', r[FMX].strip() if FMX>=0 else '')
# report blocks that have any spec with a fip=2 tier
print("BLOCKS WITH A GENUINE FIP=2 (mixed) SPEC:")
n_specs=0; n_rows=0
for i,b in enumerate(blocks,1):
    qual={sn:t for sn,t in b['fips'].items() if '2' in t}
    if not qual: continue
    for sn,t in qual.items():
        n_specs+=1; n_rows+=len(t)
    print(f"  blk#{i} product='{b['product'][:34]}' O={sorted(b['origins'])} S={sorted(b['sellers'])[:1]} protein={b['protein']}")
    for sn,t in qual.items():
        print(f"       spec='{sn}' fip1={t.get('1')} fip2={t.get('2')}")
print(f"\nGENUINE FIP specs (have fip=2) = {n_specs} -> {n_rows} rows (fip1+fip2)")
# also list ALL blocks that had ANY fip=1 (for contrast)
anyfip=[i for i,b in enumerate(blocks,1) if b['fips']]
print(f"blocks with ANY fip row (1 or 2) = {len(anyfip)}; blocks with a fip=2 = {sum(1 for b in blocks if any('2' in t for t in b['fips'].values()))}")
