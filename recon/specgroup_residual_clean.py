# -*- coding: utf-8 -*-
"""Delete stale child rows left on SURVIVING groups after the collapse upsert: spec details whose
(group,spec) isn't in the rebuilt 'Spec Group Spec' sheet + product junctions whose (group,code) isn't
in 'Spec Group x Product'. Child-first (fips of those details first). Backup. GTMS_APPLY=1 to run."""
import os, re, csv, psycopg2
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
BK='/home/src/recon/backup/prod_delete'; os.makedirs(BK,exist_ok=True); APPLY=os.environ.get('GTMS_APPLY')=='1'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t): return svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute().get('values',[])
def d2(v):
    h=[c.strip() for c in v[0]]; return [dict(zip(h,r+['']*(len(h)-len(r)))) for r in v[1:]]
sheet_det={(nrm(r['SpecGroupName2']),nrm(r['SpecName'])) for r in d2(getj('Spec Group Spec'))}
sheet_jun={(nrm(r['spec_group']),r['code'].strip().upper()) for r in d2(getj('Spec Group x Product'))}
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("""select d.id,g.name,s.name from master_specification_details d
  join master_specification_groups g on g.id=d.specification_group_id
  join master_specifications s on s.id=d.specification_id""")
stale_det=[i for i,gn,sn in cur.fetchall() if (nrm(gn),nrm(sn)) not in sheet_det]
cur.execute("""select pg.id,g.name,p.code from product_specification_groups pg
  join master_specification_groups g on g.id=pg.specification_group_id
  join master_products p on p.id=pg.product_id""")
stale_jun=[i for i,gn,cd in cur.fetchall() if (nrm(gn),str(cd).strip().upper()) not in sheet_jun]
cur.execute("select count(*) from master_specification_fips where specification_detail_id = any(%s)",(stale_det,)); nfip=cur.fetchone()[0]
print(f"MODE={'*** APPLY ***' if APPLY else 'DRY-RUN'} | stale details={len(stale_det)} (fips on them={nfip}) | stale junctions={len(stale_jun)}")
assert len(stale_det)<30 and len(stale_jun)<30, "too many stale - aborting"
if not APPLY: print("DRY-RUN. GTMS_APPLY=1 to run."); c.close(); raise SystemExit
for tbl,q,p in [('master_specification_fips',"select * from master_specification_fips where specification_detail_id = any(%s)",(stale_det,)),
                ('master_specification_details',"select * from master_specification_details where id = any(%s)",(stale_det,)),
                ('product_specification_groups',"select * from product_specification_groups where id = any(%s)",(stale_jun,))]:
    cur.execute(q,p); rows=cur.fetchall()
    if rows:
        with open(f"{BK}/{tbl}.residual-del.csv","w",newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
cur.execute("delete from master_specification_fips where specification_detail_id = any(%s)",(stale_det,)); print("deleted fips",cur.rowcount)
cur.execute("delete from master_specification_details where id = any(%s)",(stale_det,)); print("deleted details",cur.rowcount)
cur.execute("delete from product_specification_groups where id = any(%s)",(stale_jun,)); print("deleted junctions",cur.rowcount)
for t in ['master_specification_groups','master_specification_details','master_specification_fips','product_specification_groups']:
    cur.execute(f"select count(*) from {t}"); print(f"  {t} now = {cur.fetchone()[0]}")
c.close(); print("RESIDUAL CLEAN DONE.")
