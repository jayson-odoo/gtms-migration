# -*- coding: utf-8 -*-
"""Reconcile 'Profit Center x Product' to the raw source (Purchasing QL Feed / QL International):
  QL FEED SDN. BHD.        -> 34 products (raw QLF section; TGQFM55 dedup'd from 35 rows)
  QL INTERNATIONAL PTE. LTD.-> 8 products (raw QLI section)
= 42 unique (profit_center, product) pairs.

The current tab wrongly assigns BOTH centers to all 39 products (78 rows). This script:
  1) rewrites the Jayson tab to the 42 desired rows (backs up the old tab),
  2) deletes the stale rows from DB counterparty_products for profit-center counterparties
     (code IS NOT NULL) that are not in the desired set (backs up deleted rows).
The junction exporter is insert-only, so the delete is what reduces 78 -> 42.
GTMS_WRITE=1 to apply. After applying, re-run lnk_load_counterparty_products (idempotent).
"""
import os, csv, psycopg2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

KEY = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
JAY = os.environ['GSHEET_ID']
TAB = 'Profit Center x Product'

QLF = 'QL FEED SDN. BHD.'
QLI = 'QL INTERNATIONAL PTE. LTD.'
DESIRED = {QLF: [
    'PMQFBAG-25KG', 'PMQFBAG-50KG', 'PMQFBAG-JUMBO', 'PMQFBAG-MAGIC', 'PMQFBAG-OBF', 'PMQFBAG-STORM',
    'TGQBSG', 'TGQBRML', 'TGQCGM', 'TGQDDG', 'TGQDDGL', 'TGQDDGW', 'TGQDMXPL', 'TGQFFL',
    'TGQFM55', 'TGQFM60', 'TGQFM63', 'TGQFM65', 'TGQFM67', 'TGQLM', 'TGQLMP', 'TGQMZ',
    'TGQRBL', 'TGQSFOR', 'TGQSFOC', 'TGQRSM', 'TGQHSBM', 'TGQSBMHP', 'TGQSBMHPL', 'TGQSB',
    'TGQWG', 'TGQWPL', 'TGQWBP', 'TGQSBMFF',
], QLI: [
    'TGQMZ', 'TGQSBM', 'TGQDDG', 'TGQCGM', 'TGQDDGSHP', 'TGQCM', 'TGQCMP', 'TGQDLM',
]}
desired_pairs = {(pc, p) for pc, prods in DESIRED.items() for p in prods}
print('desired: QLF=%d  QLI=%d  total unique=%d'
      % (len(DESIRED[QLF]), len(DESIRED[QLI]), len(desired_pairs)))

# --- 1. rewrite the Jayson tab ---
svc = build('sheets', 'v4', credentials=Credentials.from_service_account_file(
    KEY, scopes=['https://www.googleapis.com/auth/spreadsheets']), cache_discovery=False)
v = svc.spreadsheets().values().get(spreadsheetId=JAY, range="'%s'" % TAB).execute().get('values', [])
hdr = [str(c).strip() for c in v[0]]
old_rows = [r for r in v[1:] if any(str(x).strip() for x in r)]
print('current tab rows=%d' % len(old_rows))
new_rows = [[pc, p] for pc in (QLF, QLI) for p in DESIRED[pc]]

# --- 2. compute DB deletes ---
conn = psycopg2.connect(host=os.environ['DB_HOST'], port=int(os.environ['DB_PORT']),
                        dbname=os.environ['DB_DATABASE'], user=os.environ['DB_USERNAME'],
                        password=os.environ['DB_PASSWORD'], connect_timeout=8)
cur = conn.cursor()
cur.execute("""select cp.id, c.name, p.code
    from counterparty_products cp
    join master_counterparties c on c.id = cp.counterparty_id and c.code is not null
    join master_products p on p.id = cp.product_id
    order by c.name, p.code""")
db_rows = cur.fetchall()   # (id, pc_name, product_code) for profit-center junction rows
print('DB profit-center junction rows=%d' % len(db_rows))
stale = [(rid, name, code) for rid, name, code in db_rows if (name, code) not in desired_pairs]
missing_in_db = desired_pairs - {(name, code) for _, name, code in db_rows}
print('STALE to delete=%d' % len(stale))
from collections import Counter
for pc, n in Counter(name for _, name, _ in stale).items():
    print('  %s: -%d  %s' % (pc, n, sorted(c for _, nm, c in stale if nm == pc)))
print('desired pairs MISSING from DB (re-migrate will insert)=%d %s'
      % (len(missing_in_db), sorted(missing_in_db)))

if os.environ.get('GTMS_WRITE') == '1':
    # backup + rewrite sheet
    with open('recon/backup/Profit Center x Product.pre-pcrecon.csv', 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(hdr); w.writerows(old_rows)
    svc.spreadsheets().values().clear(spreadsheetId=JAY, range="'%s'" % TAB).execute()
    svc.spreadsheets().values().update(spreadsheetId=JAY, range="'%s'!A1" % TAB,
        valueInputOption='RAW', body={'values': [hdr] + new_rows}).execute()
    print('WROTE %d rows to %r (was %d).' % (len(new_rows), TAB, len(old_rows)))
    # backup + delete stale DB rows
    if stale:
        with open('recon/backup/counterparty_products.deleted-pcrecon.csv', 'w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['id', 'profit_center', 'product'])
            w.writerows(stale)
        cur.execute('delete from counterparty_products where id = any(%s)', ([rid for rid, _, _ in stale],))
        conn.commit()
        print('DELETED %d stale rows from counterparty_products. Backup recon/backup/counterparty_products.deleted-pcrecon.csv' % cur.rowcount)
    cur.execute('select count(*) from counterparty_products cp join master_counterparties c on c.id=cp.counterparty_id and c.code is not null')
    print('profit-center junction rows now=%d' % cur.fetchone()[0])
else:
    print('\n(dry-run; GTMS_WRITE=1 to apply, then re-run lnk_load_counterparty_products)')
conn.close()
