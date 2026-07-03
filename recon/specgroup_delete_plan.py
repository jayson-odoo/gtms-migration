# -*- coding: utf-8 -*-
"""READ-ONLY prod. Plan the final delete so master_specification_groups ends at exactly the 68 sheet
names, one db row each. Classifies every db group: SURVIVE-keep / REDUNDANT-dup (name in sheet but not
the chosen keeper) / STALE (name not in sheet). Keeper per name = the id referenced by transactional
tables if any, else the id with the most spec details, else min id. Verifies no transactional ref
points at any to-be-deleted id."""
import os, re, psycopg2
from collections import defaultdict
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
sg=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroup'").execute().get('values',[])
ni=[x.strip() for x in sg[0]].index('name'); sheet_names={nrm(r[ni]) for r in sg[1:] if len(r)>ni and r[ni].strip()}
sheet_exact={r[ni].strip() for r in sg[1:] if len(r)>ni and r[ni].strip()}   # exact strings
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("select id,name from master_specification_groups"); allg=cur.fetchall()
by_name=defaultdict(list)
for i,n in allg: by_name[nrm(n)].append((i,n))
# detail counts
cur.execute("select specification_group_id, count(*) from master_specification_details group by 1")
ndet=dict(cur.fetchall())
# transactional refs per group id
refset=defaultdict(int)
for tbl,col in [('contract_specifications','specification_group_id'),('physical_contracts','specification_group_id'),('vessel_nominations','final_specification_group_id')]:
    cur.execute(f"select {col}, count(*) from {tbl} where {col} is not null group by 1")
    for g,cnt in cur.fetchall(): refset[g]+=cnt
print(f"db groups={len(allg)} | sheet names={len(sheet_names)}")
keep=set(); redundant=[]; stale=[]
for nm,ids in by_name.items():
    if nm in sheet_names:
        if len(ids)==1: keep.add(ids[0][0]); continue
        # choose keeper: prefer EXACT sheet-name match, then transactional-referenced, then most details
        exact=[i for i,n in ids if n.strip() in sheet_exact]
        refd=[i for i,_ in ids if refset.get(i)]
        if exact: keeper=max(exact, key=lambda i:(ndet.get(i,0), -i))
        elif refd: keeper=refd[0]
        else: keeper=max((i for i,_ in ids), key=lambda i:(ndet.get(i,0), -i))
        keep.add(keeper)
        for i,n in ids:
            if i!=keeper: redundant.append((i,n))
    else:
        for i,n in ids: stale.append((i,n))
delset=[i for i,_ in stale]+[i for i,_ in redundant]
print(f"KEEP={len(keep)} (target 68) | STALE={len(stale)} | REDUNDANT dup-name={len(redundant)} | DELETE total={len(delset)}")
print(f"\nnames mapping to >1 db id (dup): ")
for nm,ids in by_name.items():
    if nm in sheet_names and len(ids)>1:
        print(f"  '{nm[:45]}' ids={[(i,ndet.get(i,0),'ref'+str(refset.get(i,0))) for i,_ in ids]} keep={[i for i,_ in ids if i in keep]}")
print(f"\nREDUNDANT (dup-name, will delete): {[(i,n[:35]) for i,n in redundant]}")
# transactional refs pointing at any delete-set id?
if delset:
    bad=0
    for tbl,col in [('contract_specifications','specification_group_id'),('physical_contracts','specification_group_id'),('vessel_nominations','final_specification_group_id')]:
        cur.execute(f"select count(*) from {tbl} where {col} = any(%s)",(delset,)); n=cur.fetchone()[0]
        if n: print(f"  !! {tbl}.{col} has {n} rows pointing at delete-set (MUST repoint first)"); bad+=n
    print(f"\ntransactional refs blocking delete: {bad} (expect 0)")
# child dependents of delete-set
cur.execute("select count(*) from master_specification_details where specification_group_id = any(%s)",(delset,)); print("child spec_details to delete:", cur.fetchone()[0])
cur.execute("select count(*) from product_specification_groups where specification_group_id = any(%s)",(delset,)); print("child product_spec_groups to delete:", cur.fetchone()[0])
print(f"\nfinal db groups after delete would be {len(allg)-len(delset)} (target 68)")
print("KEEP ids sample:", sorted(keep)[:10], "..." )
c.close(); print("DELETE PLAN DONE (read-only).")
