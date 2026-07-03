# -*- coding: utf-8 -*-
"""Delete the 69 obsolete spec groups (60 stale name-not-in-sheet + 9 old whitespace-variant dups)
so master_specification_groups ends at exactly the 68 sheet names, one row each. Keeper per dup name =
exact sheet-name match. FK-safe: asserts 0 transactional refs (contract_specifications/physical_contracts/
vessel_nominations) to the delete-set, then deletes child-first (fips->details->product junctions->groups).
Backs up every deleted row. GTMS_APPLY=1 to execute (else dry-run)."""
import os, re, csv, psycopg2
from collections import defaultdict
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
BK='/home/src/recon/backup/prod_delete'; os.makedirs(BK,exist_ok=True)
APPLY=os.environ.get('GTMS_APPLY')=='1'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
sg=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroup'").execute().get('values',[])
ni=[x.strip() for x in sg[0]].index('name')
sheet_names={nrm(r[ni]) for r in sg[1:] if len(r)>ni and r[ni].strip()}
sheet_exact={r[ni].strip() for r in sg[1:] if len(r)>ni and r[ni].strip()}
assert len(sheet_names)==68, f"sheet names={len(sheet_names)}!=68"
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("select id,name from master_specification_groups"); allg=cur.fetchall()
by_name=defaultdict(list)
for i,n in allg: by_name[nrm(n)].append((i,n))
cur.execute("select specification_group_id, count(*) from master_specification_details group by 1"); ndet=dict(cur.fetchall())
refset=defaultdict(int)
for tbl,col in [('contract_specifications','specification_group_id'),('physical_contracts','specification_group_id'),('vessel_nominations','final_specification_group_id')]:
    cur.execute(f"select {col}, count(*) from {tbl} where {col} is not null group by 1")
    for g,cnt in cur.fetchall(): refset[g]+=cnt
keep=set(); delset=[]
for nm,ids in by_name.items():
    if nm in sheet_names:
        if len(ids)==1: keep.add(ids[0][0]); continue
        exact=[i for i,n in ids if n.strip() in sheet_exact]
        refd=[i for i,_ in ids if refset.get(i)]
        keeper=(max(exact,key=lambda i:(ndet.get(i,0),-i)) if exact else (refd[0] if refd else max((i for i,_ in ids),key=lambda i:(ndet.get(i,0),-i))))
        keep.add(keeper); delset += [i for i,_ in ids if i!=keeper]
    else:
        delset += [i for i,_ in ids]
print(f"db groups={len(allg)} | KEEP={len(keep)} | DELETE={len(delset)} | MODE={'*** APPLY ***' if APPLY else 'DRY-RUN'}")
assert len(keep)==68, f"KEEP={len(keep)}!=68 - aborting"
assert len(delset)<90, f"delete-set {len(delset)} implausibly large - aborting"
# FK guard
block=0
for tbl,col in [('contract_specifications','specification_group_id'),('physical_contracts','specification_group_id'),('vessel_nominations','final_specification_group_id')]:
    cur.execute(f"select count(*) from {tbl} where {col} = any(%s)",(delset,)); block+=cur.fetchone()[0]
print(f"transactional refs to delete-set: {block} (must be 0)")
assert block==0, "transactional refs still point at delete-set - repoint first, aborting"
cur.execute("select id from master_specification_details where specification_group_id = any(%s)",(delset,)); detids=[r[0] for r in cur.fetchall()]
cur.execute("select count(*) from master_specification_fips where specification_detail_id = any(%s)",(detids,)); nfip=cur.fetchone()[0]
print(f"child rows: details={len(detids)} fips={nfip} product_spec_groups=", end='')
cur.execute("select count(*) from product_specification_groups where specification_group_id = any(%s)",(delset,)); print(cur.fetchone()[0])
if not APPLY:
    print("DRY-RUN. GTMS_APPLY=1 to execute."); c.close(); raise SystemExit
# backup then delete child-first
for tbl,q,p in [('master_specification_fips',"select * from master_specification_fips where specification_detail_id = any(%s)",(detids,)),
                ('master_specification_details',"select * from master_specification_details where specification_group_id = any(%s)",(delset,)),
                ('product_specification_groups',"select * from product_specification_groups where specification_group_id = any(%s)",(delset,)),
                ('master_specification_groups',"select * from master_specification_groups where id = any(%s)",(delset,))]:
    cur.execute(q,p); rows=cur.fetchall()
    if rows:
        with open(f"{BK}/{tbl}.collapse-del.csv","w",newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
cur.execute("delete from master_specification_fips where specification_detail_id = any(%s)",(detids,)); print("deleted fips", cur.rowcount)
cur.execute("delete from master_specification_details where specification_group_id = any(%s)",(delset,)); print("deleted details", cur.rowcount)
cur.execute("delete from product_specification_groups where specification_group_id = any(%s)",(delset,)); print("deleted product_spec_groups", cur.rowcount)
cur.execute("delete from master_specification_groups where id = any(%s)",(delset,)); print("deleted groups", cur.rowcount)
# verify
for t in ['master_specification_groups','master_specification_details','master_specification_fips','product_specification_groups']:
    cur.execute(f"select count(*) from {t}"); print(f"  {t} now = {cur.fetchone()[0]}")
cur.execute("select count(distinct name) from master_specification_groups"); print("  distinct group names now =", cur.fetchone()[0])
cur.execute("select name,count(*) from master_specification_groups group by name having count(*)>1"); dd=cur.fetchall()
print("  residual duplicate names:", dd if dd else "none")
c.close(); print("DELETE DONE.")
