# -*- coding: utf-8 -*-
"""Repoint transactional refs off the 2 stale spec groups (1,125) onto their surviving collapse targets
BEFORE deleting the stale groups. Verified 1:1 by product+name (specgroup_repoint_plan2). Backs up
affected rows, runs UPDATEs, verifies 0 residual refs. GTMS_APPLY=1 to execute (else dry-run)."""
import os, csv, psycopg2
BK='/home/src/recon/backup/prod_delete'; os.makedirs(BK,exist_ok=True)
APPLY=os.environ.get('GTMS_APPLY')=='1'
# (table, group_col, old_gid, new_gid)
REPOINT=[('contract_specifications','specification_group_id',1,126),
         ('contract_specifications','specification_group_id',125,143),
         ('vessel_nominations','final_specification_group_id',1,126)]
NAMES={1:'ARGENTINA / BRAZILIAN MAIZE ->126 ARGENTINA / BRAZIL MAIZE',125:'LOCAL-MALAYSIA DMX ->143 MALAYSIA DMX PLUS MOLD INHIBITOR'}
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
# sanity: targets exist & survive
cur.execute("select id,name from master_specification_groups where id in (126,143)")
print("targets:", cur.fetchall())
print("MODE=", "*** APPLY ***" if APPLY else "DRY-RUN")
for tbl,col,old,new in REPOINT:
    cur.execute(f"select count(*) from {tbl} where {col}=%s",(old,))
    n=cur.fetchone()[0]
    print(f"  {tbl}.{col}: {n} rows @ gid={old} -> {new}   [{NAMES.get(old,'')}]")
    if APPLY and n:
        # backup
        cur.execute(f"select * from {tbl} where {col}=%s",(old,)); rows=cur.fetchall()
        with open(f"{BK}/{tbl}.repoint-{old}.csv","w",newline='') as f:
            w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
        cur.execute(f"update {tbl} set {col}=%s where {col}=%s",(new,old)); print(f"     updated {cur.rowcount} rows (backup {tbl}.repoint-{old}.csv)")
if APPLY:
    resid=0
    for tbl,col,old,new in REPOINT:
        cur.execute(f"select count(*) from {tbl} where {col}=%s",(old,)); r=cur.fetchone()[0]; resid+=r
    print(f"\nRESIDUAL refs to stale gids after repoint: {resid} (expect 0)")
else:
    print("\nDRY-RUN. GTMS_APPLY=1 to execute.")
c.close()
