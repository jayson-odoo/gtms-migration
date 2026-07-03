# -*- coding: utf-8 -*-
"""Dedup case-variant payment terms created by the case-sensitive upsert (source '14 days' vs old
'14 Days' etc). Keep the source-cased row (name exactly in sheet), delete the old-cased dup + its
configs/counterparties. Verified: none of the deleted ids are referenced by contracts. Backup + dry-run
default (GTMS_DELETE=1)."""
import os, re, csv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from gtms_migration.utils.pg import get_connection
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DO=os.environ.get('GTMS_DELETE','dry')=='1'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']),cache_discovery=False)
sh=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Payment Term'").execute().get('values',[])
ni=[x.strip() for x in sh[0]].index('name'); sheet_exact={r[ni].strip() for r in sh[1:] if len(r)>ni and r[ni].strip()}
c=get_connection(); c.autocommit=True; cur=c.cursor()
cur.execute('select id,name from master_payment_terms'); db=cur.fetchall()
from collections import defaultdict
groups=defaultdict(list)
for i,n in db: groups[nrm(n)].append((i,n))
delete=[]
for k,rows in groups.items():
    if len(rows)<2: continue
    keep=[r for r in rows if r[1] in sheet_exact]
    if not keep: keep=[min(rows)]           # fallback: lowest id
    kid=keep[0][0]
    for i,n in rows:
        if i!=kid: delete.append((i,n,kid))
print("MODE=", "*** LIVE DELETE ***" if DO else "DRY-RUN")
print(f"case-dup rows to delete: {len(delete)}")
for i,n,kid in delete: print(f"   delete id={i} {n!r} (keep {kid})")
dids=[i for i,_,_ in delete]
if not dids: print("no case dups."); raise SystemExit
# safety: none referenced by transactional tables
for t in ['physical_contracts','billing_documents','non_trade_contracts']:
    cur.execute(f'select count(*) from {t} where payment_term_id=any(%s)',(dids,)); n=cur.fetchone()[0]
    print(f"   {t} refs to delete-ids: {n}")
    assert n==0, f"{t} references a delete-id! abort"
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    for t in ['payment_term_configs','payment_term_counterparties','master_payment_terms']:
        col='id' if t=='master_payment_terms' else 'payment_term_id'
        cur.execute(f'select * from {t} where {col}=any(%s)',(dids,)); rows=cur.fetchall()
        if rows:
            with open(f'{bkd}/{t}.case-dup.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
    cur.execute('delete from payment_term_configs where payment_term_id=any(%s)',(dids,)); print("deleted configs",cur.rowcount)
    cur.execute('delete from payment_term_counterparties where payment_term_id=any(%s)',(dids,)); print("deleted cp",cur.rowcount)
    cur.execute('delete from master_payment_terms where id=any(%s)',(dids,)); print("deleted terms",cur.rowcount)
    for t in ['master_payment_terms','payment_term_configs','payment_term_counterparties']:
        cur.execute(f'select count(*) from {t}'); print(f"  {t} now = {cur.fetchone()[0]}")
else: print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
