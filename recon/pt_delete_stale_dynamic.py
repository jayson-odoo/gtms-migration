# -*- coding: utf-8 -*-
"""Delete stale payment terms (db name NOT in current sheet 'Payment Term') + their dependents, after the
trim-to-30 re-migration left old-named rows behind. Dynamic FK discovery for safety. Backup + dry-run
default (GTMS_DELETE=1 to execute)."""
import os, re, csv, psycopg2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DO=os.environ.get('GTMS_DELETE','dry')=='1'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
sh=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Payment Term'").execute().get('values',[])
ni=[x.strip() for x in sh[0]].index('name')
sheet_names={nrm(r[ni]) for r in sh[1:] if len(r)>ni and r[ni].strip()}
print("sheet payment terms:",len(sheet_names))
c=psycopg2.connect(host='host.docker.internal',port=int(os.environ.get('DB_PORT',5432)),dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("select id,name from master_payment_terms"); alldb=cur.fetchall()
stale=[(i,n) for i,n in alldb if nrm(n) not in sheet_names]; ids=[i for i,_ in stale]
print("MODE=", "*** LIVE DELETE ***" if DO else "DRY-RUN")
print(f"db payment terms={len(alldb)} | stale={len(stale)}")
for i,n in sorted(stale,key=lambda x:x[1]): print(f"   id={i} {n!r}")
if not ids: print("nothing stale."); c.close(); raise SystemExit
if len(stale)>45: print("!! SAFETY ABORT >45"); c.close(); raise SystemExit(1)
# dynamic FK dependents of master_payment_terms
cur.execute("""select tc.table_name, kcu.column_name from information_schema.table_constraints tc
 join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
 join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name
 where tc.constraint_type='FOREIGN KEY' and ccu.table_name='master_payment_terms'""")
deps=cur.fetchall(); print("FK dependents:",deps)
JUNC={'payment_term_configs','payment_term_counterparties'}
inuse=set()
for t,col in deps:
    if t in JUNC: continue
    cur.execute(f'select distinct "{col}" from "{t}" where "{col}"=any(%s)',(ids,))
    for (tid,) in cur.fetchall(): inuse.add(tid)
if inuse:
    keepnames=[n for i,n in stale if i in inuse]
    print(f"\nKEEP {len(inuse)} in-use terms (referenced by physical_contracts/billing_documents): {keepnames}")
    ids=[i for i in ids if i not in inuse]
    print(f"-> deleting {len(ids)} UNUSED stale terms (skipping in-use)")
for t,col in deps:
    cur.execute(f'select count(*) from "{t}" where "{col}"=any(%s)',(ids,)); print(f"   {t}.{col}: {cur.fetchone()[0]} rows to delete")
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    for t,col in list(deps)+[('master_payment_terms','id')]:
        cur.execute(f'select * from "{t}" where "{col}"=any(%s)',(ids,)); rows=cur.fetchall()
        if rows:
            with open(f'{bkd}/{t}.stale-pt2.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
    for t,col in deps:
        cur.execute(f'delete from "{t}" where "{col}"=any(%s)',(ids,)); print(f"deleted {cur.rowcount} from {t}")
    cur.execute("delete from master_payment_terms where id=any(%s)",(ids,)); print(f"deleted {cur.rowcount} payment terms")
    for t in ['master_payment_terms','payment_term_configs','payment_term_counterparties']:
        cur.execute(f"select count(*) from {t}"); print(f"  {t} now = {cur.fetchone()[0]}")
else: print("DRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
