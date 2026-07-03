# -*- coding: utf-8 -*-
"""Delete stale old-named cpl counterparties (code IS NULL, name not in current sheet) + FK children.
Dynamic FK discovery. Dry-run default; GTMS_DELETE=1 to execute. Backup."""
import os, re, csv, time, psycopg2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DO=os.environ.get('GTMS_DELETE','dry')=='1'
def nrm(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute().get('values',[])
h=[c.strip() for c in v[0]]; ni=h.index('name')
sheet_names={nrm(r[ni]) for r in v[1:] if len(r)>ni and r[ni].strip()}
c=psycopg2.connect(host='host.docker.internal',port=int(os.environ.get('DB_PORT',5432)),dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
cur.execute("select id,name from master_counterparties where code is null")
stale=[(i,n) for i,n in cur.fetchall() if nrm(n) not in sheet_names]
ids=[i for i,_ in stale]
print("MODE=", "*** LIVE DELETE ***" if DO else "DRY-RUN")
print(f"sheet cpl names={len(sheet_names)} | stale db counterparties (code null, name not in sheet)={len(stale)}")
for i,n in sorted(stale,key=lambda x:x[1]): print(f"   id={i} {n}")
if len(stale)>40: print("!! SAFETY ABORT >40"); c.close(); raise SystemExit(1)
if not ids: print("nothing stale."); c.close(); raise SystemExit
cur.execute("""select tc.table_name, kcu.column_name from information_schema.table_constraints tc
 join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name and tc.table_schema=kcu.table_schema
 join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name and tc.table_schema=ccu.table_schema
 where tc.constraint_type='FOREIGN KEY' and ccu.table_name='master_counterparties' and ccu.column_name='id'""")
deps=cur.fetchall(); print(f"\nFK dependents referencing stale ids:")
plan=[]
for t,col in deps:
    cur.execute(f'select count(*) from "{t}" where "{col}" = any(%s)',(ids,)); n=cur.fetchone()[0]
    if n: print(f"   {t}.{col}: {n}"); plan.append((t,col,n))
if DO:
    bkd='/home/src/recon/backup/prod_delete'; os.makedirs(bkd,exist_ok=True)
    for t,col,_ in plan:
        cur.execute(f'select * from "{t}" where "{col}" = any(%s)',(ids,)); rows=cur.fetchall()
        with open(f'{bkd}/{t}.stale-cp.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
        cur.execute(f'delete from "{t}" where "{col}" = any(%s)',(ids,)); print(f"deleted {cur.rowcount} from {t}")
    cur.execute("select * from master_counterparties where id = any(%s)",(ids,)); rows=cur.fetchall()
    with open(f'{bkd}/master_counterparties.stale-cp.csv','w',newline='') as f: w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(rows)
    cur.execute("delete from master_counterparties where id = any(%s)",(ids,)); print(f"deleted {cur.rowcount} counterparties")
    cur.execute("select count(*) from master_counterparties where code is null"); print("cpl counterparties now =",cur.fetchone()[0])
else: print("\nDRY-RUN. GTMS_DELETE=1 to execute.")
c.close()
