# -*- coding: utf-8 -*-
"""Delete the 2 user-approved stale (pre-rename) counterparties id256 PK AGRO / id297 POET NUTRITION LLC,
superseded by the corrected-name rows. Verified 0 FK dependents. Backup + dry-run default (GTMS_DELETE=1)."""
import os, csv
from gtms_migration.utils.pg import get_connection
DO=os.environ.get('GTMS_DELETE','dry')=='1'
IDS=[256,297]
c=get_connection(); c.autocommit=True; cur=c.cursor()
cur.execute("select id,name,code from master_counterparties where id=any(%s)",(IDS,)); rows=cur.fetchall()
print("MODE=", "*** LIVE DELETE ***" if DO else "DRY-RUN"); print("targets:",rows)
# safety: recompute FK refs across all dependents == 0
cur.execute("""select tc.table_name, kcu.column_name from information_schema.table_constraints tc
 join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
 join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name
 where tc.constraint_type='FOREIGN KEY' and ccu.table_name='master_counterparties'""")
tot=0
for t,col in cur.fetchall():
    cur.execute(f'select count(*) from "{t}" where "{col}"=any(%s)',(IDS,)); tot+=cur.fetchone()[0]
print("FK refs:",tot); assert tot==0, "has FK deps - abort (repoint first)"
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    cur.execute("select * from master_counterparties where id=any(%s)",(IDS,)); rr=cur.fetchall()
    with open(f'{bkd}/master_counterparties.stale-rename.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rr)
    cur.execute("delete from master_counterparties where id=any(%s)",(IDS,)); print("deleted",cur.rowcount)
    cur.execute("select count(*) from master_counterparties"); print("master_counterparties now =",cur.fetchone()[0])
else: print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
