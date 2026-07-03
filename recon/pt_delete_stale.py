# -*- coding: utf-8 -*-
"""Delete the 2 stale (pre-rename) payment terms id13 '7 Days' / id21 'Prompt Payment' and their now-
redundant junction rows (id51/52 carry the current ones). Backup + dry-run default (GTMS_DELETE=1 to run)."""
import os, csv, psycopg2
STALE=[13,21]
DO=os.environ.get('GTMS_DELETE','dry')=='1'
c=psycopg2.connect(host='host.docker.internal',port=int(os.environ.get('DB_PORT',5432)),dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
print("MODE =", "*** LIVE DELETE ***" if DO else "DRY-RUN")
cur.execute("select id,name from master_payment_terms where id=any(%s)",(STALE,)); print("stale terms:",cur.fetchall())
# safety: ensure the replacement terms carry junctions
cur.execute("select payment_term_id,count(*) from payment_term_configs where payment_term_id in (51,52) group by payment_term_id")
print("replacement configs (id51/52):", cur.fetchall())
deps=[('payment_term_counterparties','payment_term_id'),('payment_term_configs','payment_term_id')]
for t,col in deps:
    cur.execute(f'select count(*) from "{t}" where "{col}"=any(%s)',(STALE,)); print(f"  {t}: {cur.fetchone()[0]} stale rows")
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    for t,col in deps+[('master_payment_terms','id')]:
        cur.execute(f'select * from "{t}" where "{col}"=any(%s)',(STALE,)); rows=cur.fetchall()
        if rows:
            cols=[d[0] for d in cur.description]
            with open(f'{bkd}/{t}.stale-pt.csv','w',newline='') as f: w=csv.writer(f); w.writerow(cols); w.writerows(rows)
    for t,col in deps:
        cur.execute(f'delete from "{t}" where "{col}"=any(%s)',(STALE,)); print(f"deleted {cur.rowcount} from {t}")
    cur.execute("delete from master_payment_terms where id=any(%s)",(STALE,)); print(f"deleted {cur.rowcount} payment terms")
    cur.execute("select count(*) from master_payment_terms"); print("master_payment_terms now =",cur.fetchone()[0])
    cur.execute("select count(*) from payment_term_configs"); print("payment_term_configs now =",cur.fetchone()[0])
else:
    print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
