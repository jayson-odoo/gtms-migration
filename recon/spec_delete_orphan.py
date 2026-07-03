# -*- coding: utf-8 -*-
"""Delete the orphaned old specification 'Sand in HCI insolible' (id311), superseded by the corrected
'Sand in HCl insoluble'. Verify no master_specification_details reference it first. Backup + dry-run
default (GTMS_DELETE=1)."""
import os, csv
from gtms_migration.utils.pg import get_connection
DO=os.environ.get('GTMS_DELETE','dry')=='1'
BAD='Sand in HCI insolible'
c=get_connection(); c.autocommit=True; cur=c.cursor()
cur.execute("select id,name from master_specifications where name=%s",(BAD,)); rows=cur.fetchall()
print("MODE=", "*** LIVE DELETE ***" if DO else "DRY-RUN"); print("target:",rows)
if not rows: print("not found (already clean)."); c.close(); raise SystemExit
ids=[r[0] for r in rows]
# how is spec referenced by details? check both a FK id col and a name col
cur.execute("select column_name from information_schema.columns where table_name='master_specification_details'")
cols=[r[0] for r in cur.fetchall()]
# corrected spec id (same name-nrm, correct spelling)
cur.execute("select id from master_specifications where name='Sand in HCl insoluble'"); good=[r[0] for r in cur.fetchall()]
print("corrected spec id(s):",good)
# detail rows still pointing at the OLD spec id311
cur.execute("select id, specification_group_id from master_specification_details where specification_id=any(%s)",(ids,))
staled=cur.fetchall(); stale_detail_ids=[r[0] for r in staled]; stale_groups=[r[1] for r in staled]
print(f"   stale detail rows @old spec: {len(staled)} (groups {stale_groups})")
# verify each stale detail has a sibling row in the SAME group referencing the corrected spec (i.e. superseded, safe)
safe=True
for did,gid in staled:
    cur.execute("select count(*) from master_specification_details where specification_group_id=%s and specification_id=any(%s)",(gid,good))
    sib=cur.fetchone()[0]
    print(f"     detail {did} group {gid}: sibling@corrected-spec={sib}")
    if sib==0: safe=False
assert safe, "a stale detail has NO corrected sibling - would lose data, abort"
# fips referencing the stale details?
cur.execute("select count(*) from master_specification_fips where specification_detail_id=any(%s)",(stale_detail_ids,)); print("   fips on stale details:",cur.fetchone()[0])
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    for t,q,p in [('master_specification_fips',"select * from master_specification_fips where specification_detail_id=any(%s)",(stale_detail_ids,)),
                  ('master_specification_details',"select * from master_specification_details where id=any(%s)",(stale_detail_ids,)),
                  ('master_specifications',"select * from master_specifications where id=any(%s)",(ids,))]:
        cur.execute(q,p); rr=cur.fetchall()
        if rr:
            with open(f'{bkd}/{t}.orphan-spec.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rr)
    cur.execute("delete from master_specification_fips where specification_detail_id=any(%s)",(stale_detail_ids,)); print("deleted fips",cur.rowcount)
    cur.execute("delete from master_specification_details where id=any(%s)",(stale_detail_ids,)); print("deleted stale details",cur.rowcount)
    cur.execute("delete from master_specifications where id=any(%s)",(ids,)); print("deleted spec",cur.rowcount)
    for t in ['master_specifications','master_specification_details']:
        cur.execute(f"select count(*) from {t}"); print(f"  {t} now = {cur.fetchone()[0]}")
else: print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
