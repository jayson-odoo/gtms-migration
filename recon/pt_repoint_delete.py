# -*- coding: utf-8 -*-
"""Repoint the 3 in-use non-source payment terms' transactional refs to their user-chosen source
equivalents, then delete the 3 stale terms + junctions. Backup + dry-run default (GTMS_DELETE=1)."""
import os, csv
from gtms_migration.utils.pg import get_connection
DO=os.environ.get('GTMS_DELETE','dry')=='1'
MAP={  # stale term name -> source term name (user-confirmed 2026-07-02)
 'Telegraphic Transfer Against Scanned Documents':'Cash Againts Scanned Documents',
 'Telegraphic Transfer Against Scanned Documents within 3 working days':'D/P at sight within 3 working days',
 'Current Week + 30 Days':'30 days',
}
TXN=['physical_contracts','billing_documents','non_trade_contracts']
JUNC=['payment_term_configs','payment_term_counterparties']
c=get_connection(); c.autocommit=True; cur=c.cursor()
def idof(name):
    cur.execute("select id from master_payment_terms where name=%s",(name,)); r=cur.fetchall()
    assert len(r)==1, f"{name!r} resolves to {len(r)} rows"; return r[0][0]
pairs=[(idof(s), idof(t), s, t) for s,t in MAP.items()]
print("MODE=", "*** LIVE ***" if DO else "DRY-RUN")
for sid,tid,s,t in pairs: print(f"   repoint id{sid} {s!r} -> id{tid} {t!r}")
sids=[p[0] for p in pairs]
bkd='/home/src/recon/backup/prod_delete'
if DO: os.makedirs(bkd,exist_ok=True)
# backup affected txn rows
if DO:
    for tbl in TXN:
        cur.execute(f'select * from {tbl} where payment_term_id=any(%s)',(sids,)); rr=cur.fetchall()
        if rr:
            with open(f'{bkd}/{tbl}.pt-repoint.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rr)
    for tbl in JUNC+['master_payment_terms']:
        col='id' if tbl=='master_payment_terms' else 'payment_term_id'
        cur.execute(f'select * from {tbl} where {col}=any(%s)',(sids,)); rr=cur.fetchall()
        if rr:
            with open(f'{bkd}/{tbl}.pt-repoint.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rr)
# repoint
for tbl in TXN:
    for sid,tid,_,_ in pairs:
        cur.execute(f'select count(*) from {tbl} where payment_term_id=%s',(sid,)); n=cur.fetchone()[0]
        if n:
            if DO: cur.execute(f'update {tbl} set payment_term_id=%s where payment_term_id=%s',(tid,sid)); print(f"   {tbl}: repointed {cur.rowcount} (id{sid}->{tid})")
            else: print(f"   {tbl}: would repoint {n} (id{sid}->{tid})")
if DO:
    for tbl in JUNC:
        cur.execute(f'delete from {tbl} where payment_term_id=any(%s)',(sids,)); print(f"deleted {cur.rowcount} from {tbl}")
    cur.execute("delete from master_payment_terms where id=any(%s)",(sids,)); print(f"deleted {cur.rowcount} terms")
    # verify no lingering refs
    for tbl in TXN:
        cur.execute(f'select count(*) from {tbl} where payment_term_id=any(%s)',(sids,)); assert cur.fetchone()[0]==0
    for t in ['master_payment_terms','payment_term_configs','payment_term_counterparties']:
        cur.execute(f'select count(*) from {t}'); print(f"  {t} now = {cur.fetchone()[0]}")
else: print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
