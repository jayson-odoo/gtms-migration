# -*- coding: utf-8 -*-
"""Delete jayson-only 'Port Container Shifting / FCL' from master_additional_costs (removed from sheet;
additive upsert leaves it in DB). FK-safe. Backup + dry-run default (GTMS_DELETE=1)."""
import os, csv
from gtms_migration.utils.pg import get_connection
DO=os.environ.get('GTMS_DELETE','dry')=='1'
NAME='Port Container Shifting / FCL'
c=get_connection(); c.autocommit=True; cur=c.cursor()
cur.execute("select id,name,additional_cost_group_id from master_additional_costs where name=%s",(NAME,)); rows=cur.fetchall()
print("MODE=", "*** LIVE ***" if DO else "DRY-RUN","targets:",rows)
if not rows: print("not found"); c.close(); raise SystemExit
ids=[r[0] for r in rows]
cur.execute("""select tc.table_name, kcu.column_name from information_schema.table_constraints tc
 join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
 join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name
 where tc.constraint_type='FOREIGN KEY' and ccu.table_name='master_additional_costs'""")
tot=0
for t,col in cur.fetchall():
    cur.execute(f'select count(*) from "{t}" where "{col}"=any(%s)',(ids,)); n=cur.fetchone()[0]; tot+=n
    if n: print(f"   FK ref {t}.{col}: {n}")
print("total FK refs:",tot); assert tot==0,"has FK deps - abort (repoint first)"
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    cur.execute("select * from master_additional_costs where id=any(%s)",(ids,)); rr=cur.fetchall()
    with open(f'{bkd}/master_additional_costs.fcl.csv','w',newline='') as f: w=csv.writer(f);w.writerow([d[0] for d in cur.description]);w.writerows(rr)
    cur.execute("delete from master_additional_costs where id=any(%s)",(ids,)); print("deleted",cur.rowcount)
    cur.execute("select count(*) from master_additional_costs"); print("master_additional_costs now =",cur.fetchone()[0])
else: print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
