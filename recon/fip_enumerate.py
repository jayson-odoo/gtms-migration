# -*- coding: utf-8 -*-
"""READ-ONLY. Enumerate EVERY raw SpecGroupFIP row with FIP in {1,2}: inherited product (last non-blank
SpecGroupName), on-row origin/seller, SpecName, min/max, FIPmin/FIPmax, FIP. Then isolate the 12 FIP=2
rows and pair each with its FIP=1 partner in the same block/spec."""
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
prod=''; origin=''; seller=''; enum=[]
for ri,r in enumerate(rows[1:],2):
    r=r+['']*(len(h)-len(r))
    if r[P].strip() and not banner(r[P]): prod=norm(r[P]); origin=''; seller=''
    if O>=0 and r[O].strip(): origin=norm(r[O])
    if S>=0 and r[S].strip() and not banner(r[S]): seller=norm(r[S])
    fv=r[FP].strip()
    if fv in ('1.0','2.0','1','2'):
        enum.append(dict(row=ri,prod=prod,origin=origin,seller=seller,spec=norm(r[SN]),
            mn=r[MN].strip(),mx=r[MX].strip(),fmn=r[FMN].strip() if FMN>=0 else '',fmx=r[FMX].strip() if FMX>=0 else '',fip='2' if fv in ('2.0','2') else '1'))
f2=[e for e in enum if e['fip']=='2']
print(f"total fip rows={len(enum)} | fip=2 rows={len(f2)}\n")
print("=== THE 12 FIP=2 ROWS (product | origin | seller | spec | protein min-max | FIPmin-FIPmax) ===")
for e in f2:
    print(f"  r{e['row']:>3} {e['prod'][:24]:24} | O={e['origin'][:22]:22} | S={e['seller'][:26]:26} | {e['spec']:8} band={e['mn']}-{e['mx']} FIP={e['fmn']}-{e['fmx']}")
# group the fip=2 by (prod,origin,seller) to see distinct groups
key=lambda e:(nk(e['prod']),nk(e['origin']),nk(e['seller']))
grps=defaultdict(list)
for e in f2: grps[key(e)].append(e)
print(f"\ndistinct (product,origin,seller) groups among the 12 fip=2 rows = {len(grps)}")
for k,items in grps.items():
    print(f"   {items[0]['prod'][:26]:26} O={items[0]['origin'][:22]:22} S={items[0]['seller'][:24]:24} x{len(items)}")
