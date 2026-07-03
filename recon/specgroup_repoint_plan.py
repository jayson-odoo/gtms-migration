# -*- coding: utf-8 -*-
"""READ-ONLY prod. Plan the contract_specifications repoint before deleting stale spec groups.
Lists every specification_group_id referenced by contract_specifications, its group name, whether
that name SURVIVES (is in the new 68-name SpecGroup sheet -> no repoint) or is STALE (needs repoint),
and proposes the surviving group to repoint to (same product via product_specification_groups, else
name/product token match). No writes."""
import os, re, time, psycopg2
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
sg=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroup'").execute().get('values',[])
ni=[x.strip() for x in sg[0]].index('name')
sheet_names={nrm(r[ni]) for r in sg[1:] if len(r)>ni and r[ni].strip()}
print("new sheet SpecGroup names:", len(sheet_names))

c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()

cur.execute("select column_name from information_schema.columns where table_name='contract_specifications' order by ordinal_position")
cols=[r[0] for r in cur.fetchall()]
print("\ncontract_specifications columns:", cols)
gcol=next((x for x in cols if 'group' in x and 'id' in x), None)
pcol=next((x for x in cols if x in ('product_id','master_product_id')), None)
print("group-id col:", gcol, "| product col:", pcol)

cur.execute("select count(*) from contract_specifications"); print("total contract_specifications rows:", cur.fetchone()[0])

# group id -> name + survives?
cur.execute("select id,name from master_specification_groups")
gid2name={i:n for i,n in cur.fetchall()}
name2ids=defaultdict(list)
for i,n in gid2name.items(): name2ids[nrm(n)].append(i)
survive_ids={i for i,n in gid2name.items() if nrm(n) in sheet_names}
print(f"master_specification_groups total={len(gid2name)} | survive(name in sheet)={len(survive_ids)} | stale={len(gid2name)-len(survive_ids)}")

# product_specification_groups: product -> surviving group ids (to propose repoint target by product)
cur.execute("select specification_group_id, product_id from product_specification_groups")
psg=cur.fetchall()
prod2surv=defaultdict(set); grp2prod=defaultdict(set)
for gidx,pid in psg:
    grp2prod[gidx].add(pid)
    if gidx in survive_ids: prod2surv[pid].add(gidx)

# what contract_specifications references
cur.execute(f"select {gcol}, count(*) from contract_specifications group by {gcol} order by count(*) desc")
refs=cur.fetchall()
print(f"\ncontract_specifications references {len(refs)} distinct {gcol} values:")
repoint=[]
for gidx,cnt in refs:
    nm=gid2name.get(gidx,'<MISSING>'); status='SURVIVES' if gidx in survive_ids else ('STALE' if gidx in gid2name else 'DANGLING')
    prods=sorted(grp2prod.get(gidx,[]))
    cand=set()
    for p in prods: cand|=prod2surv.get(p,set())
    cand=sorted(cand)
    print(f"  group_id={gidx} [{status}] rows={cnt} name='{nm[:55]}' products={prods} -> surviving_groups_same_product={[(g,gid2name[g][:40]) for g in cand]}")
    if status!='SURVIVES':
        repoint.append((gidx,nm,cnt,prods,cand))

# also show the actual contract_specifications rows for stale refs (full detail)
if repoint:
    stale_ids=[g for g,_,_,_,_ in repoint]
    cur.execute(f"select id, {gcol}, {pcol if pcol else 'null'}, * from contract_specifications where {gcol} = any(%s) order by {gcol}",(stale_ids,))
    print(f"\nSTALE-referencing contract_specifications rows (need repoint): {len(repoint)} groups")
print("\nREPOINT PLAN DONE (read-only).")
c.close()
