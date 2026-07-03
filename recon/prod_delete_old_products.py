# -*- coding: utf-8 -*-
"""PHASE 2 cleanup: delete SUPERSEDED old products (and their FK children) from PROD after run_all.
Superseded = product codes that were remapped away or dropped in the re-master (from recon/out/product_map.json).
Dynamically discovers every table with a FK to master_products so no dependent is missed.
SAFETY: dry-run by default. Set env GTMS_DELETE=1 to actually delete (child-first, per-row autocommit,
FK-error tolerant). Never touches products that are in the 39-target generic master."""
import os, json, psycopg2
MAP=json.load(open('/home/src/recon/out/product_map.json'))
mapping=MAP['mapping']; dropped=set(MAP['dropped']); targets=set(MAP['targets'])
# superseded old codes = remapped-away (target != self) + dropped
REMOVE={jc for jc,t in mapping.items() if t!=jc} | dropped
# junction tables run_all regenerates -> DELETE old rows. Everything else (transactional) -> REPOINT.
JUNCTION={'counterparty_products','product_contract_types','product_specification_groups',
          'master_price_index_products','master_uom_conversions','master_lot_to_uom_conversions',
          'contract_term_products','inventory_location_packaging_fees'}
# repoint target for a superseded code = its generic map target; dropped-but-referenced get an explicit target
REPOINT_OVERRIDE={'TGQHDMX7':'TGQDMXPL'}  # user: repoint DMX-7 refs to DMX PLUS
def repoint_code(old): return mapping.get(old) or REPOINT_OVERRIDE.get(old)
DO = os.environ.get('GTMS_DELETE','dry')=='1'
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
print(f"MODE = {'*** LIVE DELETE ***' if DO else 'DRY-RUN (report only)'}")
print(f"superseded codes to remove (from mapping) = {len(REMOVE)}")
# resolve to prod product ids (only those actually present in prod, and NOT in the keep-targets)
cur.execute("select id, code from master_products where code = any(%s)", (list(REMOVE),))
found=[(i,code) for i,code in cur.fetchall() if code not in targets]
ids=[i for i,_ in found]
id2code={i:code for i,code in found}
# full prod code->id (to resolve repoint targets, which must exist post-run_all)
cur.execute("select code, id from master_products"); code2id={c:i for c,i in cur.fetchall()}
print(f"matching prod master_products rows = {len(found)}")
for i,code in sorted(found, key=lambda x:x[1]): print(f"    id={i:5} {code}")
# also report which superseded codes are NOT in prod (nothing to delete) and any target overlap
notinprod=sorted(REMOVE - {code for _,code in found})
print(f"superseded codes not present in prod (no-op) = {len(notinprod)}: {notinprod}")
if not ids:
    print("\nNothing to delete on prod."); c.close(); raise SystemExit
# discover FK dependents of master_products
cur.execute("""
select tc.table_name, kcu.column_name
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name and tc.table_schema=kcu.table_schema
join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name and tc.table_schema=ccu.table_schema
where tc.constraint_type='FOREIGN KEY' and ccu.table_name='master_products' and ccu.column_name='id'
order by tc.table_name""")
deps=cur.fetchall()
print(f"\nFK dependents of master_products = {len(deps)} (classified DELETE=junction / REPOINT=transactional):")
del_plan=[]; repoint_plan=[]; blockers=[]
for tbl,col in deps:
    cur.execute(f'select "{col}", count(*) from "{tbl}" where "{col}" = any(%s) group by "{col}"', (ids,))
    per=cur.fetchall(); n=sum(x[1] for x in per)
    if n==0: continue
    if tbl in JUNCTION:
        del_plan.append((tbl,col,n)); print(f"    DELETE  {tbl}.{col}: {n}")
    else:
        # repoint: resolve each old product id -> new prod id
        for pid,cnt in per:
            old=id2code[pid]; newc=repoint_code(old); newid=code2id.get(newc)
            status=f"-> {newc}(id {newid})" if newid else f"-> {newc} MISSING IN PROD (run_all first!)"
            if not newid: blockers.append((tbl,old,newc))
            repoint_plan.append((tbl,col,pid,newid,cnt))
            print(f"    REPOINT {tbl}.{col}: {cnt} row(s) {old} {status}")
print(f"\nplan: DELETE {sum(n for _,_,n in del_plan)} junction rows across {len(del_plan)} tables; "
      f"REPOINT {sum(c for *_,c in repoint_plan)} transactional rows; then delete {len(ids)} products")
if blockers:
    print("\n!! REPOINT BLOCKERS (target product not in prod yet - run_all BEFORE deleting):")
    for t,o,n in blockers: print(f"     {t}: {o} -> {n}")

if DO:
    if blockers:
        print("\nABORT: repoint targets missing in prod. Run run_all first, then re-run."); c.close(); raise SystemExit(1)
    # BACKUP every affected row first (reversibility)
    import csv, os
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd, exist_ok=True)
    dc=c.cursor()
    for tbl,col in deps:
        dc.execute(f'select * from "{tbl}" where "{col}" = any(%s)', (ids,))
        rows=dc.fetchall()
        if not rows: continue
        cols=[d[0] for d in dc.description]
        with open(f'{bkd}/{tbl}.csv','w',newline='') as f:
            w=csv.writer(f); w.writerow(cols); w.writerows(rows)
        print(f"    backed up {len(rows)} rows of {tbl} -> recon/backup/prod_delete/{tbl}.csv")
    dc.execute("select * from master_products where id = any(%s)", (ids,))
    prows=dc.fetchall(); pcols=[d[0] for d in dc.description]
    with open(f'{bkd}/master_products.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(pcols); w.writerows(prows)
    print(f"    backed up {len(prows)} master_products -> recon/backup/prod_delete/master_products.csv")
    print("\n--- REPOINTING transactional refs ---")
    for tbl,col,pid,newid,cnt in repoint_plan:
        cur.execute(f'update "{tbl}" set "{col}"=%s where "{col}"=%s', (newid,pid)); print(f"    repointed {cur.rowcount} in {tbl} ({id2code[pid]}->id{newid})")
    print("--- DELETING junction children ---")
    for tbl,col,_ in del_plan:
        cur.execute(f'delete from "{tbl}" where "{col}" = any(%s)', (ids,)); print(f"    deleted {cur.rowcount} from {tbl}")
    print("--- DELETING old products ---")
    d=0
    for i in ids:
        try: cur.execute("delete from master_products where id=%s", (i,)); d+=cur.rowcount
        except Exception as e: print(f"    ERR product id={i} ({id2code[i]}): {str(e)[:80]}")
    print(f"    deleted {d} master_products rows")
    cur.execute("select count(*) from master_products"); print("master_products now =", cur.fetchone()[0])
else:
    print("\nDRY-RUN only. Sequence: run_all -> re-dry-run (blockers clear) -> GTMS_DELETE=1.")
c.close()
