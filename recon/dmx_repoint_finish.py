# -*- coding: utf-8 -*-
"""User-approved: repoint contract_specifications from old DMX-7 group 26 -> DMX PLUS group 125
(spec values unchanged, reference only), then delete empty group 26. Backup."""
import os, csv
from gtms_migration.utils.pg import get_connection
OLD,NEW=26,125
c=get_connection(); c.autocommit=True; cur=c.cursor()
# sanity: 125 exists w/ specs, 26 empty
cur.execute("select name from master_specification_groups where id=%s",(NEW,)); assert cur.fetchone(), "125 missing"
cur.execute("select count(*) from master_specification_details where specification_group_id=%s",(OLD,)); assert cur.fetchone()[0]==0, "26 still has details"
bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
cur.execute("select * from contract_specifications where specification_group_id=%s",(OLD,)); rr=cur.fetchall()
with open(f'{bkd}/contract_specifications.dmx-repoint.csv','w',newline='') as f: w=csv.writer(f);w.writerow([d[0] for d in cur.description]);w.writerows(rr)
print(f"backed up {len(rr)} contract_specifications rows")
cur.execute("update contract_specifications set specification_group_id=%s where specification_group_id=%s",(NEW,OLD)); print("repointed",cur.rowcount,"contract_specifications 26->125")
# any other FK dependents of group 26?
cur.execute("""select tc.table_name,kcu.column_name from information_schema.table_constraints tc
 join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
 join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name
 where tc.constraint_type='FOREIGN KEY' and ccu.table_name='master_specification_groups'""")
for t,col in cur.fetchall():
    cur.execute(f'select count(*) from "{t}" where "{col}"=%s',(OLD,)); n=cur.fetchone()[0]
    if n: print(f"   still refs group 26: {t}.{col}={n}")
cur.execute("delete from master_specification_groups where id=%s",(OLD,)); print("deleted group 26, rowcount",cur.rowcount)
cur.execute("select count(*) from master_specification_groups"); print("master_specification_groups now =",cur.fetchone()[0])
c.close()
