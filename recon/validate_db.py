# -*- coding: utf-8 -*-
"""VALIDATION (2): Jayson sheet vs PROD DB. Single-key master tables -> row-level diff by business key
(missing_in_db / extra_in_db). Compound/junction tables -> count comparison. Writes
'VALIDATION Jayson-vs-DB (Summary)' + '(Details)'. Read-only. Needs the prod tunnel."""
import os, re, time, psycopg2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t):
    try: return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
    except Exception: return None
def jkeys(tab, col):
    v=getj(tab)
    if not v: return None,None
    h=[str(c).strip() for c in v[0]]
    ci=next((i for i,c in enumerate(h) if nk(c)==nk(col)), None)
    if ci is None: return None,None
    ks=[nk(r[ci]) for r in v[1:] if len(r)>ci and str(r[ci]).strip()]
    return ks, {nk(r[ci]):(r[ci].strip()) for r in v[1:] if len(r)>ci and str(r[ci]).strip()}
def jcount(tab):
    v=getj(tab); return (len([r for r in v[1:] if any(str(x).strip() for x in r)]) if v else None)

c=psycopg2.connect(host=os.environ.get('DB_HOST','host.docker.internal'),port=int(os.environ.get('DB_PORT',5432)),
    dbname=os.environ['DB_DATABASE'],user=os.environ['DB_USERNAME'],password=os.environ['DB_PASSWORD'],connect_timeout=8)
cur=c.cursor()
def dbkeys(table, col, where=''):
    cur.execute(f'select "{col}" from "{table}"'+(f' where {where}' if where else ''))
    rows=[nk(r[0]) for r in cur.fetchall() if r[0] is not None and str(r[0]).strip()]
    return rows
def dbcount(table, where=''):
    cur.execute(f'select count(*) from "{table}"'+(f' where {where}' if where else '')); return cur.fetchone()[0]

# (jayson_tab, db_table, sheet_key_col, db_key_col, db_where)
SINGLE=[
 ('Products','master_products','code','code',''),
 ('Payment Term','master_payment_terms','name','name',''),
 ('Packing Unit','master_packing_units','code','code',''),
 ('UoM','master_uoms','code','code',''),
 ('Ports','master_ports','code','code',''),
 ('Legal Entity','master_legal_entities','code','code',''),
 ('Trader (Salesperson)','master_traders','code','code',''),
 ('Tax','master_taxes','code','code',''),
 ('Incoterm','master_incoterms','code','code',''),
 ('Contract Type','master_contract_types','code','code',''),
 ('Contract Terms','master_contract_terms','name','name',''),
 ('Specifications','master_specifications','name','name',''),
 ('SpecGroup','master_specification_groups','name','name',''),
 ('Additonal Costs','master_additional_costs','name','name',''),
 ('Counterparty Group','master_counterparty_groups','name','name',''),
 ('Document Template','master_document_templates','name','name',''),
 ('Price Index','master_price_indexes','code','code',''),
 ('Price Buildup Component','master_price_build_up_components','code','code',''),
]
# count-only (compound/FK-resolved keys): (jayson_tab, db_table, db_where, note)
COUNT=[
 ('Counterparty v2','master_counterparties','code IS NULL','sheet incl ~4-5 rows flagged Unique/Duplicate=Duplicate (excluded by design incl S W KHEW/YEN HUAT); rest match'),
 ('Inventory Locations','master_inventory_locations','','code+legal_entity key'),
 ('Addresses','addresses','','address+city+postcode+state key'),
 ('Business Units','master_business_units','','id key'),
 ('Profit Center x Product','counterparty_products','','FK compound'),
 ('Product x Contract Type','product_contract_types','','FK compound'),
 ('Spec Group x Product','product_specification_groups','','FK compound'),
 ('Price Index Product','master_price_index_products','','FK compound'),
 ('Product UoM Conversion','master_uom_conversions','','FK compound'),
 ('Product Lot to UoM Conversion','master_lot_to_uom_conversions','','FK compound'),
 ('Contract Term x Product','contract_term_products','','FK compound'),
 ('Inventory Location Packing Charges','inventory_location_packaging_fees','','FK compound'),
 ('Spec Group Spec','master_specification_details','','FK compound'),
 ('SpecGroupFIP','master_specification_fips','','FK compound'),
 ('Payment Term Configs','payment_term_configs','','FK compound'),
 ('Users','users','','email key (+system seed users)'),
 ('Roles','roles','','name+guard'),
]
summary=[['entity','db_table','mode','sheet_rows','db_rows','missing_in_db','extra_in_db','note']]
details=[['entity','key_value','diff_type','db_table']]
DCAP=1500
for tab,tbl,sk,dk,where in SINGLE:
    ks,kmap=jkeys(tab,sk)
    if ks is None: summary.append([tab,tbl,'single','?','?','','',f'sheet col {sk!r} not found']); continue
    try: dks=dbkeys(tbl,dk,where)
    except Exception as e: summary.append([tab,tbl,'single',len(ks),'ERR','','',str(e)[:60]]); c.rollback(); continue
    sset,dset=set(ks),set(dks)
    miss=sorted(sset-dset); extra=sorted(dset-sset)
    summary.append([tab,tbl,'row-diff',len(ks),len(dks),len(miss),len(extra),''])
    for k in miss:
        if len(details)<DCAP: details.append([tab, kmap.get(k,k),'MISSING_IN_DB',tbl])
    for k in extra:
        if len(details)<DCAP: details.append([tab, k,'EXTRA_IN_DB',tbl])
    print(f"{tab:26} sheet={len(ks):4} db={len(dks):4} miss={len(miss):3} extra={len(extra):3}")
for tab,tbl,where,note in COUNT:
    sc=jcount(tab)
    try: dc=dbcount(tbl,where)
    except Exception as e: dc=f'ERR {str(e)[:40]}'; c.rollback()
    summary.append([tab,tbl,'count',sc,dc,'','',note])
    print(f"{tab:26} sheet={sc} db={dc}  (count-only: {note})")
def write(title, rows):
    meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=JAY).execute())
    if title not in [s['properties']['title'] for s in meta['sheets']]:
        retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
write('VALIDATION Jayson-vs-DB (Summary)', summary)
write('VALIDATION Jayson-vs-DB (Details)', details)
print(f"\nwrote report tabs: Summary ({len(summary)-1}), Details ({len(details)-1})")
c.close()
