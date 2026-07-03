# -*- coding: utf-8 -*-
"""Seed the 'Product Lot to UoM Conversion' Jayson tab so every product has a row (39 total).
Maize/soybean/soybean-meal keep their CBOT lot->uom multipliers (already present, non-1);
the remaining flat-price products get multiplier = 1. Only the flat-price products currently
MISSING from the tab are appended (existing rows untouched). GTMS_WRITE=1 to apply.

After applying, re-run the cpp lot-to-uom pipeline (mage run gtms_migration cpp_load_master_lot_to_uom_conversions).
"""
import os, csv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

KEY = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
JAY = os.environ['GSHEET_ID']
TAB = 'Product Lot to UoM Conversion'

# Flat-price products missing from the tab -> multiplier 1. (code, ref, description)
MISSING = [
    ('TGQCM',     'CM',    'CANOLA MEAL'),
    ('TGQDLM',    'DLM',   'D-L METHIONINE'),
    ('TGQDMXPL',  'DMXPL', 'DMX PLUS MOLD INHIBITOR'),
    ('TGQSBMFF',  'SBMFF', 'FULL FAT SOYA BEAN MEAL'),
    ('TGQSBMHP',  'SBMHP', 'HI-PRO SOYA BEAN MEAL'),
    ('TGQWBP',    'WBP',   'WHEAT BRAN PELLET'),
]

svc = build('sheets', 'v4', credentials=Credentials.from_service_account_file(
    KEY, scopes=['https://www.googleapis.com/auth/spreadsheets']), cache_discovery=False)
v = svc.spreadsheets().values().get(spreadsheetId=JAY, range="'%s'" % TAB).execute().get('values', [])
hdr = [str(c).strip() for c in v[0]]
existing_rows = [r for r in v[1:] if any(str(x).strip() for x in r)]
have = {str(r[0]).strip() for r in existing_rows if r}
print('header:', hdr)
print('existing products=%d' % len(have))

col = {'code': 0, 'contract_number_reference': 1, 'description': 2, 'UoM': 3, 'multiplier': 4}
to_add = []
for code, ref, desc in MISSING:
    if code in have:
        print('  already present, skip:', code)
        continue
    row = [''] * len(hdr)
    vals = {'code': code, 'contract_number_reference': ref, 'description': desc, 'UoM': 'MT', 'multiplier': '1'}
    for h in hdr:
        if h in vals:
            row[hdr.index(h)] = vals[h]
    to_add.append(row)
    print('  +add', code, '-> MT x1')

print('\nexisting=%d  adding=%d  final=%d' % (len(existing_rows), len(to_add), len(existing_rows) + len(to_add)))
if not to_add:
    print('nothing to add.'); raise SystemExit(0)

out_rows = existing_rows + to_add
if os.environ.get('GTMS_WRITE') == '1':
    with open('recon/backup/Product Lot to UoM Conversion.pre-seed39.csv', 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(hdr); w.writerows(existing_rows)
    svc.spreadsheets().values().clear(spreadsheetId=JAY, range="'%s'" % TAB).execute()
    svc.spreadsheets().values().update(
        spreadsheetId=JAY, range="'%s'!A1" % TAB, valueInputOption='RAW',
        body={'values': [hdr] + out_rows}).execute()
    print('WROTE %d rows to %r. Backup recon/backup/Product Lot to UoM Conversion.pre-seed39.csv'
          % (len(out_rows), TAB))
else:
    print('(dry-run; GTMS_WRITE=1 to apply)')
