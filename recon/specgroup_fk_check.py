# -*- coding: utf-8 -*-
"""READ-ONLY prod. Verify FK targets before repoint/delete: (1) all FK constraints referencing
master_specification_groups (who blocks a group delete), (2) what contract_specifications.specification_id
points to (must be master_specifications, NOT master_specification_details we will delete)."""
import os, psycopg2
from google.oauth2.service_account import Credentials
c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
c.autocommit=True; cur=c.cursor()
q="""select tc.table_name, kcu.column_name, ccu.table_name as ref_table, ccu.column_name as ref_col
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name
where tc.constraint_type='FOREIGN KEY' and ccu.table_name in
  ('master_specification_groups','master_specification_details','master_specifications')
order by ccu.table_name, tc.table_name"""
cur.execute(q)
print("FKs pointing AT spec tables (child_table.child_col -> ref_table.ref_col):")
for t,cc,rt,rcol in cur.fetchall(): print(f"  {t}.{cc} -> {rt}.{rcol}")
# FKs FROM contract_specifications
cur.execute("""select kcu.column_name, ccu.table_name, ccu.column_name
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu on tc.constraint_name=kcu.constraint_name
join information_schema.constraint_column_usage ccu on tc.constraint_name=ccu.constraint_name
where tc.constraint_type='FOREIGN KEY' and tc.table_name='contract_specifications'""")
print("\ncontract_specifications FKs:")
for cc,rt,rcol in cur.fetchall(): print(f"  contract_specifications.{cc} -> {rt}.{rcol}")
# sanity: do the referenced specification_id values exist in master_specifications?
cur.execute("select count(*) from contract_specifications cs where cs.specification_id is not null and not exists (select 1 from master_specifications m where m.id=cs.specification_id)")
print("\ncontract_specifications.specification_id NOT in master_specifications:", cur.fetchone()[0])
cur.execute("select count(*) from contract_specifications cs where cs.specification_id is not null and exists (select 1 from master_specification_details d where d.id=cs.specification_id)")
print("contract_specifications.specification_id that ARE master_specification_details ids (danger):", cur.fetchone()[0])
c.close()
print("FK CHECK DONE.")
