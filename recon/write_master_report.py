# -*- coding: utf-8 -*-
"""Write consolidated MASTER raw-vs-jayson discrepancy report with WHY + status, all entities."""
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
# entity, raw_src, raw, jayson, discrepancy, WHY, status
R=[['entity','raw source','raw','jayson','discrepancy','WHY','status']]
rows=[
 ['Products','Purchasing Products',39,39,'none','Re-mastered to generic raw products (origin lives in spec groups)','ALIGNED'],
 ['Counterparty v2','Acct QLF+QLI Vendor+Customer','424 codes','423 codes','1 raw code unmatched','Names overwritten from raw by M3 code; V+C merged to 1 row; excluded all-Duplicate-flagged; 1 code TBD','~ALIGNED'],
 ['Additonal Costs','Additional Charges + Inv Loc Charges',246,253,'onlyRaw 2 / onlyJay 1','23 storage/warehouse charges added; 2 raw-only are GROUP HEADERS not line-items; 1 jayson variant','MINIMIZED (by-design residual)'],
 ['Payment Term','PT files (1H2h + 1RNaMj)',30,48,'onlyRaw 12 / onlyJay 30','Jayson is a CURATED SUPERSET (full names + variants); 12 raw codes join-fuzzy (raw=codes, jayson=full text)','BY-DESIGN (jayson richer)'],
 ['SpecGroup (groups)','Purchasing SpecGroup blocks','75 blk/34 prod',85,'onlyRaw 1','Jayson expands 1 group per origin/seller variant; +6 gap groups added; 1 raw product has no group','MINIMIZED'],
 ['Spec Group Spec','Purchasing SpecGroup lines',509,794,'jayson superset','Jayson expands spec lines per (expanded) group; fully covers raw','ALIGNED (superset)'],
 ['SpecGroupFIP','Purchasing SpecGroupFIP',363,48,'jayson much smaller','FIP only for MIXED 1:1/2:1 tiers (HI-PRO SOYA Protein). Raw 363 = mostly single-band specs that are NOT FIP','CORRECT (scope, by-design)'],
 ['Ports','Shipping Ports',70,37,'raw>jayson','Raw uses berth/2-letter codes (local berths + intl); jayson=37 standard GTMS intl ports','BY-DESIGN (diff code system)'],
 ['Inventory Locations','Shipping Inv Location',38,39,'~32 field diffs (port_code 32, id 15, name 3)','port_code differs = raw berth/2-letter port codes vs jayson GTMS port codes (SAME convention as Ports); id=surrogate keys (not meaningful); name/location_type minor','BY-DESIGN (port code system)'],
 ['Tax','Acct Tax',47,45,'onlyRaw 2','E0/V0 taxes intentionally skipped (seed-deleted from prod earlier)','BY-DESIGN'],
 ['Trader (Salesperson)','Acct Trader',13,13,'13 field changes','Jayson curated fuller names (e.g. PHANG JUNN KIN vs raw PHANG JUNN)','BY-DESIGN (jayson curated)'],
 ['Packing Unit','Acct/Purchasing Packing',22,21,'onlyRaw 1 / 5 changes','raw code=M3 vs jayson code=GTMS (alias original_code); 5 description diffs; 1 raw-only','MINOR'],
 ['Users','GTMS User ID List',29,33,'onlyJay 4','4 jayson = SYSTEM seed users (system@, etc.) not in raw','BY-DESIGN'],
 ['Legal Entity','Acct Legal Entity',1,2,'onlyJay 1','Jayson has QL International added (raw file is QLF-only here)','BY-DESIGN'],
 ['Profit Centers','Acct Profit Centers',1,2,'onlyJay 1','Jayson has both QLF + QLI profit centers','BY-DESIGN'],
 ['Countries','Acct Countries',241,240,'~1','Raw has instruction-row header (max-length hints), no real key; foundational/stable','FOUNDATIONAL'],
 ['States','Acct States',397,437,'jayson superset','Raw instruction-row header; jayson superset; MH bad-country noted (user fixing)','FOUNDATIONAL'],
 ['UoM','Acct UoM',47,48,'~1','Raw instruction-row header (no key); +1 jayson','FOUNDATIONAL'],
 ['Business Units','Acct Business Units',1,1,'none','Aligned','ALIGNED'],
 ['Regions','Acct Regions',3,3,'none','Aligned','ALIGNED'],
 ['Vendor (tab)','Acct Vendor',167,'-','superseded','DEAD tab - superseded by Counterparty v2 (do not migrate)','SUPERSEDED'],
 ['Customer (tab)','Acct Customer',280,'-','superseded','DEAD tab - superseded by Counterparty v2 (do not migrate)','SUPERSEDED'],
]
R+=rows
note=[['MASTER raw-vs-Jayson discrepancy summary + WHY. Detail tabs: VALIDATION Jayson-vs-Raw (Details), ...(v2). Status: ALIGNED/MINIMIZED=ok; BY-DESIGN/FOUNDATIONAL/SUPERSEDED=expected; NEEDS REVIEW=open.']]
title='VALIDATION Raw-vs-Jayson MASTER'
meta=svc.spreadsheets().get(spreadsheetId=JAY).execute()
if title not in [s['properties']['title'] for s in meta['sheets']]:
    svc.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute()
svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':note+[[]]+R}).execute()
print(f"wrote '{title}' with {len(rows)} entities")
from collections import Counter
print("status counts:", dict(Counter(r[6] for r in rows)))
