# -*- coding: utf-8 -*-
"""READ-ONLY prod. Find stale child rows on SURVIVING groups: spec details whose (group,spec) isn't in
the rebuilt 'Spec Group Spec' sheet, and product junctions whose (group,code) isn't in 'Spec Group x
Product'. These are leftovers upsert didn't remove."""
import os, re, psycopg2
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t): return svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute().get('values',[])
def d2(v):
    h=[c.strip() for c in v[0]]; return [dict(zip(h,r+['']*(len(h)-len(r)))) for r in v[1:]]
ss=d2(getj('Spec Group Spec')); sx=d2(getj('Spec Group x Product'))
sheet_det={(nrm(r['SpecGroupName2']),nrm(r['SpecName'])) for r in ss}
sheet_jun={(nrm(r['spec_group']),r['code'].strip().upper()) for r in sx}
print(f"sheet details pairs={len(sheet_det)} | sheet junction pairs={len(sheet_jun)}")
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("""select d.id, g.name, s.name from master_specification_details d
  join master_specification_groups g on g.id=d.specification_group_id
  join master_specifications s on s.id=d.specification_id""")
det=cur.fetchall()
stale_det=[(i,gn,sn) for i,gn,sn in det if (nrm(gn),nrm(sn)) not in sheet_det]
print(f"\ndb details={len(det)} | STALE (not in sheet)={len(stale_det)}:")
for i,gn,sn in stale_det: print(f"   det_id={i} grp='{gn[:45]}' spec='{sn}'")
cur.execute("""select pg.id, g.name, p.code from product_specification_groups pg
  join master_specification_groups g on g.id=pg.specification_group_id
  join master_products p on p.id=pg.product_id""")
jun=cur.fetchall()
stale_jun=[(i,gn,cd) for i,gn,cd in jun if (nrm(gn),str(cd).strip().upper()) not in sheet_jun]
print(f"\ndb junctions={len(jun)} | STALE (not in sheet)={len(stale_jun)}:")
for i,gn,cd in stale_jun: print(f"   psg_id={i} grp='{gn[:45]}' code={cd}")
c.close(); print("\nRESIDUAL PROBE DONE (read-only).")
