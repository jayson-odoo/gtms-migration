# -*- coding: utf-8 -*-
"""Delete stale OLD-named spec groups (db names not in current sheet after (IND)/(VN) rename) + their
dependents. Whitespace-normalized match. Backup + dry-run default (GTMS_DELETE=1 to run)."""
import os, re, csv, time, psycopg2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DO=os.environ.get('GTMS_DELETE','dry')=='1'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
_sg=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroup'").execute().get('values',[])
_ni=[x.strip() for x in _sg[0]].index('name')
sheet_names={nrm(r[_ni]) for r in _sg[1:] if len(r)>_ni and r[_ni].strip()}
print("sheet spec groups:", len(sheet_names))
c=psycopg2.connect(host='host.docker.internal',port=int(os.environ.get('DB_PORT',5432)),dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("select id,name from master_specification_groups")
alldb=cur.fetchall()
stale=[(i,n) for i,n in alldb if nrm(n) not in sheet_names]
ids=[i for i,_ in stale]
print("MODE=", "*** LIVE DELETE ***" if DO else "DRY-RUN")
print(f"db spec groups={len(alldb)} | stale (not in sheet)={len(stale)}")
for i,n in sorted(stale, key=lambda x:x[1]): print(f"   id={i} {n}")
if len(stale) > 40:
    print("!! SAFETY ABORT: >40 stale is implausible (expected ~28) - check matching."); c.close(); raise SystemExit(1)
if not ids: print("nothing stale."); c.close(); raise SystemExit
cur.execute("select id from master_specification_details where specification_group_id = any(%s)",(ids,))
detids=[r[0] for r in cur.fetchall()]
cur.execute("select count(*) from master_specification_fips where specification_detail_id = any(%s)",(detids,)); nfip=cur.fetchone()[0]
cur.execute("select count(*) from product_specification_groups where specification_group_id = any(%s)",(ids,)); npsg=cur.fetchone()[0]
print(f"\ndependents: spec_details={len(detids)} spec_fips={nfip} product_specification_groups={npsg}")
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    for tbl,q in [('master_specification_fips',("select * from master_specification_fips where specification_detail_id = any(%s)",(detids,))),
                  ('master_specification_details',("select * from master_specification_details where specification_group_id = any(%s)",(ids,))),
                  ('product_specification_groups',("select * from product_specification_groups where specification_group_id = any(%s)",(ids,))),
                  ('master_specification_groups',("select * from master_specification_groups where id = any(%s)",(ids,)))]:
        cur.execute(*q); rows=cur.fetchall()
        if rows:
            with open(f'{bkd}/{tbl}.stale-sg.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
    cur.execute("delete from master_specification_fips where specification_detail_id = any(%s)",(detids,)); print("deleted fips",cur.rowcount)
    cur.execute("delete from master_specification_details where specification_group_id = any(%s)",(ids,)); print("deleted details",cur.rowcount)
    cur.execute("delete from product_specification_groups where specification_group_id = any(%s)",(ids,)); print("deleted psg",cur.rowcount)
    cur.execute("delete from master_specification_groups where id = any(%s)",(ids,)); print("deleted groups",cur.rowcount)
    for t in ['master_specification_groups','master_specification_details','master_specification_fips','product_specification_groups']:
        cur.execute(f"select count(*) from {t}"); print(f"  {t} now = {cur.fetchone()[0]}")
else: print("\nDRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
