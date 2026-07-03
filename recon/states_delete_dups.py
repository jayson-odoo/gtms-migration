# -*- coding: utf-8 -*-
"""Delete the 4 all-caps duplicate state rows (18 QUEENSLAND, 21 HENAN, 23 JAWA BARAT, 24 WEST KALIMANTAN);
proper-case twins (41/95/165/167) kept. Verified 0 master_ports FK refs. Backup + dry-run (GTMS_DELETE=1)."""
import os, csv
from gtms_migration.utils.pg import get_connection
DO=os.environ.get('GTMS_DELETE','dry')=='1'
IDS=[18,21,23,24]
c=get_connection();c.autocommit=True;cur=c.cursor()
cur.execute("select id,name,country from master_states where id=any(%s)",(IDS,)); print("MODE=", "*** LIVE ***" if DO else "DRY-RUN","targets:",cur.fetchall())
cur.execute("select count(*) from master_ports where state_id=any(%s)",(IDS,)); n=cur.fetchone()[0]
print("master_ports refs:",n); assert n==0,"FK refs - abort"
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    cur.execute("select * from master_states where id=any(%s)",(IDS,)); rr=cur.fetchall()
    with open(f'{bkd}/master_states.case-dup.csv','w',newline='') as f: w=csv.writer(f);w.writerow([d[0] for d in cur.description]);w.writerows(rr)
    cur.execute("delete from master_states where id=any(%s)",(IDS,)); print("deleted",cur.rowcount)
    cur.execute("select count(*) from master_states"); print("master_states now =",cur.fetchone()[0])
else: print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
