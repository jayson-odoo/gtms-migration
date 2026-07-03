# -*- coding: utf-8 -*-
"""Reconcile prod master_specification_fips to the corrected 24-row SpecGroupFIP sheet: delete prod FIP
rows whose (group name, spec name, fip) isn't in the sheet (the 12 extra on groups that lack the
'Non-Reciprocal Allowances 2:1' tier). Backup + child-safe (fips are leaves). GTMS_APPLY=1 to run."""
import os, re, csv, psycopg2
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
BK='/home/src/recon/backup/prod_delete'; os.makedirs(BK,exist_ok=True); APPLY=os.environ.get('GTMS_APPLY')=='1'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
def nfip(s): return str(s).strip().rstrip('0').rstrip('.') if '.' in str(s) else str(s).strip()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
fv=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroupFIP'").execute().get('values',[])
fh=[c.strip() for c in fv[0]]
gi=lambda n: fh.index(n)
GN,SN,FP=gi('SpecGroupName'),gi('SpecName'),gi('fip')
sheet_fip={(nrm(r[GN]),nrm(r[SN]),nfip(r[FP])) for r in fv[1:] if len(r)>FP and r[GN].strip()}
print(f"sheet SpecGroupFIP rows={len(fv)-1} | distinct keys={len(sheet_fip)}")
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("""select f.id, g.name, s.name, f.fip from master_specification_fips f
  join master_specification_details d on d.id=f.specification_detail_id
  join master_specification_groups g on g.id=d.specification_group_id
  join master_specifications s on s.id=d.specification_id""")
prod=cur.fetchall()
stale=[(fid,gn,sn,fp) for fid,gn,sn,fp in prod if (nrm(gn),nrm(sn),nfip(fp)) not in sheet_fip]
print(f"prod fips={len(prod)} | STALE (not in 24-row sheet)={len(stale)} | MODE={'*** APPLY ***' if APPLY else 'DRY-RUN'}")
for fid,gn,sn,fp in stale: print(f"   del fip_id={fid} grp='{gn[:48]}' spec={sn} fip={fp}")
assert len(stale)<20, "too many stale fips - aborting"
if not APPLY: print("DRY-RUN. GTMS_APPLY=1 to run."); c.close(); raise SystemExit
ids=[fid for fid,_,_,_ in stale]
cur.execute("select * from master_specification_fips where id = any(%s)",(ids,)); rows=cur.fetchall()
with open(f"{BK}/master_specification_fips.fipfix-del.csv","w",newline='') as fh2: w=csv.writer(fh2); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
cur.execute("delete from master_specification_fips where id = any(%s)",(ids,)); print("deleted fips", cur.rowcount)
cur.execute("select count(*) from master_specification_fips"); print("master_specification_fips now =", cur.fetchone()[0])
c.close(); print("FIP PROD FIX DONE.")
