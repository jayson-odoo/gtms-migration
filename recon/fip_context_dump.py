# -*- coding: utf-8 -*-
"""READ-ONLY. For each fip=2 row in the LOCAL SpecGroupFIP tab, print the row + the 8 rows above it
(cols SpecGroupName/Origin/Seller/SpecName/min/max/FIP) so we can read each fip=2 row's TRUE group
identity (seller / IND variant) instead of guessing."""
import glob, re
import openpyxl
D='/home/src/raw_master/300626'
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroupFIP']
rows=[[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]; wb.close()
h=[norm(x) for x in rows[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,MN,MX,FP=[gi(x) for x in ['SpecGroupName','SpecGroupName3 (Origin)','SpecGroupName4 (Seller)','SpecName','minimum','maximum','FIP']]
def cell(r,i):
    r=r+['']*(len(h)-len(r)); return r[i] if i>=0 else ''
f2idx=[i for i,r in enumerate(rows) if cell(r,FP) in ('2.0','2')]
print(f"fip=2 row indices: {f2idx}\n")
for idx in f2idx:
    print(f"----- fip=2 at row {idx+1} -----")
    for j in range(max(1,idx-8), idx+1):
        r=rows[j]
        g,o,s,sn,mn,mx,fp=cell(r,P),cell(r,O),cell(r,S),cell(r,SN),cell(r,MN),cell(r,MX),cell(r,FP)
        if not any([g,o,s,sn,fp]): continue
        mark='  <== FIP2' if j==idx else ''
        print(f"   r{j+1:>3} G='{g[:26]:26}' O='{o[:18]:18}' S='{s[:24]:24}' spec='{sn[:12]:12}' {mn}-{mx} fip={fp}{mark}")
    print()
