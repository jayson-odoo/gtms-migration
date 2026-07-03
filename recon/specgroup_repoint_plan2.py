# -*- coding: utf-8 -*-
"""READ-ONLY prod. Full repoint plan across ALL 3 transactional tables that FK master_specification_groups:
contract_specifications.specification_group_id, physical_contracts.specification_group_id,
vessel_nominations.final_specification_group_id. For each referenced STALE group, propose the surviving
same-product group to repoint to."""
import os, re, psycopg2
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
sg=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroup'").execute().get('values',[])
ni=[x.strip() for x in sg[0]].index('name'); sheet_names={nrm(r[ni]) for r in sg[1:] if len(r)>ni and r[ni].strip()}
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("select id,name from master_specification_groups")
gid2name={i:n for i,n in cur.fetchall()}
survive={i for i,n in gid2name.items() if nrm(n) in sheet_names}
cur.execute("select specification_group_id, product_id from product_specification_groups")
prod2surv=defaultdict(set); grp2prod=defaultdict(set)
for g,p in cur.fetchall():
    grp2prod[g].add(p)
    if g in survive: prod2surv[p].add(g)
def propose(gidx):
    cand=set()
    for p in grp2prod.get(gidx,[]): cand|=prod2surv.get(p,set())
    return sorted(cand)
TAB=[('contract_specifications','specification_group_id'),
     ('physical_contracts','specification_group_id'),
     ('vessel_nominations','final_specification_group_id')]
for tbl,col in TAB:
    cur.execute(f"select {col}, count(*) from {tbl} where {col} is not null group by {col} order by 2 desc")
    refs=cur.fetchall()
    print(f"\n=== {tbl}.{col} : {len(refs)} distinct non-null group ids ===")
    for gidx,cnt in refs:
        nm=gid2name.get(gidx,'<MISSING>'); st='SURVIVES' if gidx in survive else ('STALE' if gidx in gid2name else 'DANGLING')
        cand=propose(gidx) if st!='SURVIVES' else []
        print(f"  gid={gidx} [{st}] rows={cnt} '{nm[:50]}'"+("" if st=='SURVIVES' else f" -> candidates {[(g,gid2name[g][:38]) for g in cand]}"))
c.close(); print("\nDONE (read-only).")
