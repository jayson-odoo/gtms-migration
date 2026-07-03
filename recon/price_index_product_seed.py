# -*- coding: utf-8 -*-
"""Seed the 'Price Index Product' Jayson tab so every related product is linked to the
FULL monthly curve of its commodity family, not just the historical subset of months.

Families are CBOT prefixes: C (Corn), S (Soybean), SM (Soybean Meal). A product's
"related families" are derived from the EXISTING 'Price Index Product' rows — i.e. we do
NOT guess new product<->commodity relationships, we only extend the months for products
that are already linked to a family. Preserves every existing row; only APPENDS the
missing (code, product) pairs. GTMS_WRITE=1 to apply (else dry-run).

After applying, re-run the `lnk_load_price_index_products` Mage pipeline to upsert the
junction into prod (idempotent: exporter is on_conflict do-nothing on (price_index_id, product_id)).
"""
import os, csv, re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

KEY = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
JAY = os.environ['GSHEET_ID']
PIX_TAB = 'Price Index'
LINK_TAB = 'Price Index Product'
FAM_RE = re.compile(r'^(SM|S|C)[FGHJKMNQUVXZ]\d\d$')   # SM before S so 'SM*' wins


def family(code):
    m = FAM_RE.match(str(code).strip())
    return m.group(1) if m else None


svc = build('sheets', 'v4',
            credentials=Credentials.from_service_account_file(
                KEY, scopes=['https://www.googleapis.com/auth/spreadsheets']),
            cache_discovery=False)


def get(tab):
    return svc.spreadsheets().values().get(
        spreadsheetId=JAY, range=f"'{tab}'").execute().get('values', [])


# --- 1. full set of price-index codes per family (from the seeded Price Index tab) ---
pv = get(PIX_TAB)
phdr = [str(c).strip() for c in pv[0]]
pi_code_col = phdr.index('code')
fam_codes = {}
for r in pv[1:]:
    if len(r) <= pi_code_col:
        continue
    code = str(r[pi_code_col]).strip()
    fam = family(code)
    if fam:
        fam_codes.setdefault(fam, set()).add(code)
print("price-index codes per family:")
for f in sorted(fam_codes):
    print(f"  {f}: {len(fam_codes[f])}  {sorted(fam_codes[f])}")

# --- 2. existing links; discover which families each product already belongs to ---
lv = get(LINK_TAB)
lhdr = [str(c).strip() for c in lv[0]]
ci, pj = lhdr.index('code'), lhdr.index('product')
existing_rows = [r for r in lv[1:] if any(str(x).strip() for x in r)]
existing_pairs = set()
prod_families = {}   # product -> set(families it is already linked to)
for r in existing_rows:
    row = (r + [''] * (len(lhdr) - len(r)))
    code, prod = str(row[ci]).strip(), str(row[pj]).strip()
    if not code or not prod:
        continue
    existing_pairs.add((code, prod))
    fam = family(code)
    if fam:
        prod_families.setdefault(prod, set()).add(fam)

# --- 3. desired = every product x FULL curve of each family it belongs to ---
to_add = []
for prod, fams in sorted(prod_families.items()):
    for fam in sorted(fams):
        for code in sorted(fam_codes.get(fam, [])):
            if (code, prod) not in existing_pairs:
                to_add.append((code, prod))

print(f"\nexisting links={len(existing_pairs)}  products={len(prod_families)}  "
      f"MISSING links to add={len(to_add)}")
by_prod = {}
for code, prod in to_add:
    by_prod.setdefault(prod, []).append(code)
for prod in sorted(by_prod):
    fams = ','.join(sorted(prod_families[prod]))
    print(f"  {prod:16} [{fams}] +{len(by_prod[prod])}: {sorted(by_prod[prod])}")

if not to_add:
    print("\nnothing to add — every related product already has its full curve.")
    raise SystemExit(0)

out_rows = existing_rows + [
    [code if h == 'code' else prod if h == 'product' else '' for h in lhdr]
    for code, prod in to_add
]

if os.environ.get('GTMS_WRITE') == '1':
    with open('recon/backup/Price Index Product.pre-fullcurve.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(lhdr)
        w.writerows(existing_rows)
    svc.spreadsheets().values().clear(
        spreadsheetId=JAY, range=f"'{LINK_TAB}'").execute()
    svc.spreadsheets().values().update(
        spreadsheetId=JAY, range=f"'{LINK_TAB}'!A1",
        valueInputOption='RAW', body={'values': [lhdr] + out_rows}).execute()
    print(f"\nWROTE {len(out_rows)} rows to '{LINK_TAB}' "
          f"(was {len(existing_rows)}). Backup recon/backup/Price Index Product.pre-fullcurve.csv")
else:
    print("\n(dry-run; GTMS_WRITE=1 to apply, then re-run lnk_load_price_index_products)")
