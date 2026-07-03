# -*- coding: utf-8 -*-
"""PROD DATA EXTRACTION for business sign-off.

Reads every migrated PROD table and writes a BUSINESS-PRESENTABLE extract to a NEW
Google Sheet so the departments can compare it, row for row, against the raw files
they submitted and sign off the migration.

Business-presentable =
  - NO `id` columns and NO `*_id` foreign keys (all surrogate ids dropped),
  - every FK resolved back to its business code/name (reverse of the pipelines'
    resolve_fk() calls),
  - Counterparties emitted as a Customer list AND a Vendor list (their M3 codes
    recovered from master_integration_references), matching how the business gave
    them to us.

Read-only: never writes to prod, never touches the Jayson working sheet.
Run inside the mage docker image (has psycopg2 + google libs), tunnel up:
  docker run --rm --env-file .env -e DB_HOST=host.docker.internal \
    -v "$PWD":/home/src -w /home/src mageai/mageai:latest python recon/extract_signoff.py
Env: EXTRACT_GSHEET_ID (optional) reuses an existing output sheet instead of creating one.
"""
import json
import os
import time
from datetime import datetime

import pandas as pd
import psycopg2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ----------------------------------------------------------------------------- setup
KEY = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
SHARE_WITH = os.environ.get('EXTRACT_SHARE_WITH', 'tehjayson@gmail.com')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
_creds = Credentials.from_service_account_file(KEY, scopes=SCOPES)
sheets = build('sheets', 'v4', credentials=_creds, cache_discovery=False)
drive = build('drive', 'v3', credentials=_creds, cache_discovery=False)

conn = psycopg2.connect(
    host=os.environ.get('DB_HOST', 'host.docker.internal'), port=int(os.environ.get('DB_PORT', 5432)),
    dbname=os.environ['DB_DATABASE'], user=os.environ['DB_USERNAME'], password=os.environ['DB_PASSWORD'],
    connect_timeout=8,
)


def read_sql(sql):
    return pd.read_sql(sql, conn)


def retry(fn):
    for _ in range(8):
        try:
            return fn()
        except HttpError as e:
            if getattr(e, 'resp', None) is not None and e.resp.status in (429, 500, 503):
                time.sleep(20)
                continue
            raise
    return fn()


# ----------------------------------------------------------------------------- FK reverse
_fk_cache = {}


def fk_map(ref_table, ref_col, where=None):
    """id -> business natural key (code / name / address) for a reference table."""
    k = (ref_table, ref_col, where)
    if k not in _fk_cache:
        w = f' where {where}' if where else ''
        df = read_sql(f'select id, "{ref_col}" from {ref_table}{w}')
        _fk_cache[k] = dict(zip(df['id'].tolist(), df[ref_col].tolist()))
    return _fk_cache[k]


DROP_ALWAYS = {'created_at', 'updated_at', 'deleted_at', 'created_by_user_id', 'updated_by_user_id',
               'logo', 'printout_logo'}
_UNRESOLVED = []  # (table, idcol, id_value) for non-null ids that didn't resolve — verification


def reverse_and_clean(df, table, fks=(), json_fks=(), keep_id=False):
    """Replace each *_id with its resolved business value (in place, same position),
    then drop id + every remaining unresolved *_id + technical columns."""
    df = df.copy()
    for spec in fks:
        idcol, ref_table, ref_col, label = spec[0], spec[1], spec[2], spec[3]
        where = spec[4] if len(spec) > 4 else None
        m = fk_map(ref_table, ref_col, where)
        pos = df.columns.get_loc(idcol)
        vals = df[idcol].map(lambda v: m.get(v) if pd.notna(v) else None)
        # record non-null ids that failed to resolve
        bad = df[df[idcol].notna() & vals.isna()][idcol].tolist()
        for b in bad:
            _UNRESOLVED.append((table, idcol, b))
        df = df.drop(columns=[idcol])
        df.insert(pos, label, vals)
    for idcol, ref_table, ref_col, label in json_fks:
        m = fk_map(ref_table, ref_col)

        def conv(v, _m=m):
            if v is None or (not isinstance(v, (list, tuple)) and pd.isna(v)):
                return None
            arr = v
            if isinstance(v, str):
                try:
                    arr = json.loads(v)
                except Exception:
                    return v
            if not isinstance(arr, (list, tuple)):
                arr = [arr]
            out = []
            for x in arr:
                try:
                    out.append(str(_m.get(int(x), _m.get(str(x), x))))
                except Exception:
                    out.append(str(_m.get(str(x), x)))
            return ', '.join(out)

        pos = df.columns.get_loc(idcol)
        vals = df[idcol].map(conv)
        df = df.drop(columns=[idcol])
        df.insert(pos, label, vals)
    # drop technical + surrogate id + any leftover unresolved *_id
    for c in list(df.columns):
        if c in DROP_ALWAYS:
            df = df.drop(columns=[c])
        elif c == 'id' and not keep_id:
            df = df.drop(columns=[c])
        elif c.endswith('_id') and c != 'id':
            df = df.drop(columns=[c])
    return df


# ----------------------------------------------------------------------------- labels
_TOKEN = {'uom': 'UoM', 'm3': 'M3', 'tin': 'TIN', 'fip': 'FIP', 'hs': 'HS', 'id': 'ID',
          'lc': 'LC', 'no': 'No', 'url': 'URL'}


def prettify(col):
    s = str(col)
    if ' ' in s:  # already a friendly label (e.g. 'M3 Code') — leave as-is
        return s
    return ' '.join(_TOKEN.get(w.lower(), w.capitalize()) for w in s.split('_'))


# ----------------------------------------------------------------------------- entity config
# fks: (id_col, ref_table, ref_natural_col, output_label[, where])
ENTITIES = [
    # ---- legal-entity group ----
    dict(tab='Countries', table='master_countries', order_by='code'),
    dict(tab='States', table='master_states', order_by='name'),
    dict(tab='Business Units', table='master_business_units', order_by='name'),
    dict(tab='Addresses', table='addresses', order_by='address'),
    dict(tab='Legal Entity', table='master_legal_entities', order_by='code', fks=[
        ('business_unit_id', 'master_business_units', 'name', 'business_unit'),
        ('address_id', 'addresses', 'address', 'address_ref'),
        ('billing_address_id', 'addresses', 'address', 'billing_address_ref'),
    ]),
    dict(tab='Profit Centers', table='master_counterparties', where='code IS NOT NULL', order_by='code', fks=[
        ('legal_entity_id', 'master_legal_entities', 'name', 'legal_entity'),
        ('counterparty_group_id', 'master_counterparty_groups', 'name', 'counterparty_group'),
    ]),
    dict(tab='Document Template', table='master_document_templates', order_by='name'),
    dict(tab='Document Content Snippet', table='master_document_content_snippets', order_by='name', fks=[
        ('document_template_id', 'master_document_templates', 'name', 'document_template'),
    ]),
    dict(tab='Payment Term', table='master_payment_terms', order_by='name'),
    # ---- products / specs group ----
    dict(tab='Packing Unit', table='master_packing_units', order_by='code'),
    dict(tab='UoM', table='master_uoms', order_by='code'),
    dict(tab='Products', table='master_products', order_by='code', fks=[
        ('packing_unit_id', 'master_packing_units', 'code', 'packing_unit'),
        ('default_uom_id', 'master_uoms', 'code', 'default_uom'),
        ('tax_id', 'master_taxes', 'code', 'tax'),
    ]),
    dict(tab='Specifications', table='master_specifications', order_by='name'),
    dict(tab='SpecGroup', table='master_specification_groups', order_by='name'),
    dict(tab='Spec Group Spec', table='master_specification_details', fks=[
        ('specification_group_id', 'master_specification_groups', 'name', 'specification_group'),
        ('specification_id', 'master_specifications', 'name', 'specification'),
    ]),
    dict(tab='SpecGroupFIP', table='master_specification_fips', fks=[
        # specification_detail_id -> resolve to (group, spec) via a composite lookup handled below
    ], handler='fips'),
    dict(tab='Product UoM Conversion', table='master_uom_conversions', fks=[
        ('product_id', 'master_products', 'code', 'product'),
        ('from_uom_id', 'master_uoms', 'code', 'from_uom'),
        ('to_uom_id', 'master_uoms', 'code', 'to_uom'),
    ]),
    dict(tab='Product Lot to UoM Conversion', table='master_lot_to_uom_conversions', fks=[
        ('product_id', 'master_products', 'code', 'product'),
        ('uom_id', 'master_uoms', 'code', 'uom'),
    ]),
    dict(tab='Price Index', table='master_price_indexes', order_by='code', fks=[
        ('contract_type_id', 'master_contract_types', 'code', 'contract_type'),
        ('source_id', 'master_external_systems', 'code', 'source'),
        ('incoterm_id', 'master_incoterms', 'code', 'incoterm'),
        ('uom_id', 'master_uoms', 'code', 'uom'),
        ('basis_port_id', 'master_ports', 'code', 'basis_port'),
    ]),
    dict(tab='Trader', table='master_traders', order_by='code'),
    dict(tab='Price Buildup Component', table='master_price_build_up_components', order_by='code'),
    dict(tab='Contract Terms', table='master_contract_terms', order_by='name'),
    dict(tab='Contract Type', table='master_contract_types', order_by='code'),
    dict(tab='Incoterm', table='master_incoterms', order_by='code'),
    dict(tab='Late Shipment Penalty', table='master_late_shipment_penalties', order_by='lower_bound_days'),
    # ---- counterparty / location group ----
    dict(tab='Counterparty Group', table='master_counterparty_groups', order_by='name'),
    dict(tab='Ports', table='master_ports', order_by='code', fks=[
        ('state_id', 'master_states', 'name', 'state'),
        ('region_id', 'master_regions', 'name', 'region'),
    ]),
    dict(tab='Inventory Locations', table='master_inventory_locations', order_by='code', fks=[
        ('legal_entity_id', 'master_legal_entities', 'name', 'legal_entity'),
        ('port_id', 'master_ports', 'code', 'port'),
        ('address_id', 'addresses', 'address', 'address_ref'),
    ]),
    # Counterparty merged + Customer/Vendor split handled specially (see below).
    # ---- additional-costs group ----
    dict(tab='Tax', table='master_taxes', order_by='code'),
    dict(tab='Additional Cost Group', table='master_additional_cost_groups', order_by='code'),
    dict(tab='Additonal Costs', table='master_additional_costs', order_by='name', fks=[
        ('additional_cost_group_id', 'master_additional_cost_groups', 'name', 'additional_cost_group'),
    ], json_fks=[
        ('profit_centers', 'master_counterparties', 'name', 'profit_centers'),
        ('contract_types', 'master_contract_types', 'name', 'contract_types'),
    ]),
    # ---- business junctions ----
    dict(tab='Profit Center x Product', table='counterparty_products', fks=[
        ('counterparty_id', 'master_counterparties', 'name', 'profit_center', 'code IS NOT NULL'),
        ('product_id', 'master_products', 'code', 'product'),
    ]),
    dict(tab='Product x Contract Type', table='product_contract_types', fks=[
        ('product_id', 'master_products', 'code', 'product'),
        ('contract_type_id', 'master_contract_types', 'code', 'contract_type'),
    ]),
    dict(tab='Spec Group x Product', table='product_specification_groups', fks=[
        ('product_id', 'master_products', 'code', 'product'),
        ('specification_group_id', 'master_specification_groups', 'name', 'specification_group'),
    ]),
    dict(tab='Price Index Product', table='master_price_index_products', fks=[
        ('price_index_id', 'master_price_indexes', 'code', 'price_index'),
        ('product_id', 'master_products', 'code', 'product'),
    ]),
    dict(tab='Contract Term x Product', table='contract_term_products', fks=[
        ('contract_term_id', 'master_contract_terms', 'name', 'contract_term'),
        ('product_id', 'master_products', 'code', 'product'),
    ]),
    dict(tab='Contract Term x Incoterm', table='contract_term_incoterms', fks=[
        ('contract_term_id', 'master_contract_terms', 'name', 'contract_term'),
        ('incoterm_id', 'master_incoterms', 'code', 'incoterm'),
    ]),
    dict(tab='Legal Entity x Tax', table='legal_entity_taxes', fks=[
        ('legal_entity_id', 'master_legal_entities', 'name', 'legal_entity'),
        ('tax_id', 'master_taxes', 'code', 'tax'),
    ]),
    dict(tab='Legal Entity x Contract Type', table='legal_entity_contract_types', fks=[
        ('legal_entity_id', 'master_legal_entities', 'name', 'legal_entity'),
        ('contract_type_id', 'master_contract_types', 'code', 'contract_type'),
    ]),
    dict(tab='Payment Term Configs', table='payment_term_configs', fks=[
        ('payment_term_id', 'master_payment_terms', 'name', 'payment_term'),
    ]),
    dict(tab='Payment Term x Profit Center', table='payment_term_counterparties', fks=[
        ('payment_term_id', 'master_payment_terms', 'name', 'payment_term'),
        ('counterparty_id', 'master_counterparties', 'name', 'counterparty', 'code IS NOT NULL'),
    ]),
    dict(tab='Inventory Location Packing Charges', table='inventory_location_packaging_fees', fks=[
        ('inventory_location_id', 'master_inventory_locations', 'code', 'inventory_location'),
        ('packaging_product_id', 'master_products', 'code', 'packaging_product'),
    ]),
    dict(tab='Integration Reference', table='master_integration_references', fks=[
        ('integratable_id', 'master_counterparties', 'name', 'counterparty'),
        ('external_system_id', 'master_external_systems', 'code', 'external_system'),
    ]),
]


# ----------------------------------------------------------------------------- special handlers
def build_fips():
    """SpecGroupFIP: specification_detail_id -> (group name, spec name) via master_specification_details."""
    df = read_sql('select * from master_specification_fips')
    det = read_sql('select id, specification_group_id, specification_id from master_specification_details')
    grp = fk_map('master_specification_groups', 'name')
    spc = fk_map('master_specifications', 'name')
    det['specification_group'] = det['specification_group_id'].map(grp)
    det['specification'] = det['specification_id'].map(spc)
    dmap_g = dict(zip(det['id'], det['specification_group']))
    dmap_s = dict(zip(det['id'], det['specification']))
    pos = df.columns.get_loc('specification_detail_id')
    df.insert(pos, 'specification_group', df['specification_detail_id'].map(dmap_g))
    df.insert(pos + 1, 'specification', df['specification_detail_id'].map(dmap_s))
    df = df.drop(columns=['specification_detail_id'])
    return reverse_and_clean(df, 'master_specification_fips')


def build_counterparty_frame():
    """master_counterparties with FKs reversed, keyed by id (for the customer/vendor join)."""
    df = read_sql('select * from master_counterparties')
    return reverse_and_clean(df, 'master_counterparties', fks=[
        ('legal_entity_id', 'master_legal_entities', 'name', 'legal_entity'),
        ('counterparty_group_id', 'master_counterparty_groups', 'name', 'counterparty_group'),
    ], keep_id=True)


def build_customer_vendor(cp):
    """Split via master_integration_references: a customer_reference_no -> Customer (that M3 code),
    a vendor_reference_no -> Vendor. Merged entities appear in both, matching the raw lists."""
    ir = read_sql('select integratable_id, vendor_reference_no, customer_reference_no '
                  'from master_integration_references')
    biz_cols = [c for c in cp.columns if c not in ('id', 'code')]  # code is NULL for these

    def side(ref_col):
        s = ir[ir[ref_col].notna() & (ir[ref_col].astype(str).str.strip() != '')].copy()
        m = s.merge(cp, left_on='integratable_id', right_on='id', how='left')
        out = pd.DataFrame({'M3 Code': m[ref_col].values})
        for c in biz_cols:
            out[c] = m[c].values
        return out.sort_values('M3 Code').reset_index(drop=True)

    return side('customer_reference_no'), side('vendor_reference_no')


# ----------------------------------------------------------------------------- sheet writer
def _values(df):
    def cell(v):
        if isinstance(v, (list, tuple, set, dict)):
            return str(v)
        return '' if pd.isna(v) else str(v)
    header = [prettify(c) for c in df.columns]
    body = [[cell(v) for v in row] for row in df.itertuples(index=False, name=None)]
    return [header] + body


def ensure_output_sheet():
    """Return an existing spreadsheet id to write to, or None (xlsx-only). The service
    account can't CREATE Drive files (no storage quota) — so to get a live Google Sheet
    the user creates an empty one, shares it with the service account (Editor), and passes
    EXTRACT_GSHEET_ID; otherwise we still produce the xlsx workbook below."""
    sid = os.environ.get('EXTRACT_GSHEET_ID')
    if sid:
        print(f'writing to Google Sheet {sid}')
        return sid
    print('EXTRACT_GSHEET_ID not set -> xlsx-only (see notes at end to also write a Google Sheet)')
    return None


_existing_tabs = None


def write_tab(sid, tab, df):
    global _existing_tabs
    if _existing_tabs is None:
        meta = retry(lambda: sheets.spreadsheets().get(spreadsheetId=sid).execute())
        _existing_tabs = [s['properties']['title'] for s in meta['sheets']]
    if tab not in _existing_tabs:
        try:
            retry(lambda: sheets.spreadsheets().batchUpdate(
                spreadsheetId=sid, body={'requests': [{'addSheet': {'properties': {'title': tab}}}]}).execute())
        except HttpError as e:
            if 'already exists' not in str(e):  # tab created concurrently / left by a prior run — fine
                raise
        _existing_tabs.append(tab)
    retry(lambda: sheets.spreadsheets().values().clear(spreadsheetId=sid, range=f"'{tab}'").execute())
    retry(lambda: sheets.spreadsheets().values().update(
        spreadsheetId=sid, range=f"'{tab}'!A1", valueInputOption='RAW', body={'values': _values(df)}).execute())


# ----------------------------------------------------------------------------- run
def write_xlsx(outputs, path):
    """outputs: list of (tab, df). Excel sheet names max 31 chars & no []:*?/\\."""
    seen = {}

    def safe(name):
        n = name.translate({ord(c): '-' for c in '[]:*?/\\'})[:31]
        if n in seen:
            seen[n] += 1
            n = f'{n[:28]}_{seen[n]}'
        seen[n] = seen.get(n, 0)
        return n
    with pd.ExcelWriter(path, engine='openpyxl') as xw:
        for tab, df in outputs:
            out = df.copy()
            out.columns = [prettify(c) for c in out.columns]
            out.to_excel(xw, sheet_name=safe(tab), index=False)
    print(f'wrote workbook: {path}')


def main():
    sid = ensure_output_sheet()
    outputs = []  # (tab, df) in order
    index = [['Tab', 'Source table', 'Rows']]

    for e in ENTITIES:
        where = f" where {e['where']}" if e.get('where') else ''
        if e.get('handler') == 'fips':
            df = build_fips()
        else:
            raw = read_sql(f"select * from {e['table']}{where}")
            df = reverse_and_clean(raw, e['table'], fks=e.get('fks', ()), json_fks=e.get('json_fks', ()))
        if e.get('order_by') and e['order_by'] in df.columns:
            df = df.sort_values(e['order_by'], kind='stable').reset_index(drop=True)
        outputs.append((e['tab'], df))
        index.append([e['tab'], e['table'], len(df)])
        print(f"  {e['tab']:34} {e['table']:34} rows={len(df)}")

    # ---- counterparty merged + customer/vendor split ----
    cp = build_counterparty_frame()
    cust, vend = build_customer_vendor(cp)
    cp_out = cp.drop(columns=['id']).sort_values('name', kind='stable').reset_index(drop=True)
    for tab, df, tbl in [('Customer', cust, 'master_counterparties (is customer)'),
                         ('Vendor', vend, 'master_counterparties (is vendor)'),
                         ('Counterparty (merged)', cp_out, 'master_counterparties')]:
        outputs.append((tab, df))
        index.append([tab, tbl, len(df)])
        print(f"  {tab:34} {tbl:34} rows={len(df)}")

    outputs.insert(0, ('_INDEX', pd.DataFrame(index[1:], columns=index[0])))

    # ---- write: always xlsx; Google Sheet if an id was provided ----
    out_path = os.environ.get('EXTRACT_XLSX', '/home/src/recon/out/prod_extract_signoff.xlsx')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    write_xlsx(outputs, out_path)
    if sid:
        for tab, df in outputs:
            write_tab(sid, tab, df)
        print(f'wrote {len(outputs)} tabs -> https://docs.google.com/spreadsheets/d/{sid}')

    # ---- verification ----
    print('\n=== VERIFICATION ===')
    if _UNRESOLVED:
        from collections import Counter
        by = Counter((t, c) for t, c, _ in _UNRESOLVED)
        print(f'!! {len(_UNRESOLVED)} non-null FK id(s) did NOT resolve, by (table,col): {dict(by)}')
        print(f'   sample: {_UNRESOLVED[:10]}')
    else:
        print('OK: every non-null FK resolved to a business value.')
    print(f'Customer rows={len(cust)}  Vendor rows={len(vend)}  Merged counterparties={len(cp_out)}')
    conn.close()


if __name__ == '__main__':
    main()
