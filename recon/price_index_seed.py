# -*- coding: utf-8 -*-
"""Seed the 'Price Index' Jayson tab with the FULL monthly curve for Corn (C/BU),
Soybean (S/BU) and Soybean Meal (SM/ST), every calendar month Jan-2025..Dec-2026
= 24 months x 3 = 72 rows. Preserves existing rows exactly; only fills missing months.
Codes = CBOT futures tickers [prefix][monthletter][YY]. GTMS_WRITE=1 to apply (else dry)."""
import os, csv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY=os.environ['GOOGLE_APPLICATION_CREDENTIALS']; JAY=os.environ['GSHEET_ID']; TAB='Price Index'
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{TAB}'").execute().get('values',[])
hdr=v[0]; existing={ r[0].strip(): (r+['']*(len(hdr)-len(r)))[:len(hdr)] for r in v[1:] if r and str(r[0]).strip()}
iCode=hdr.index('code')
LET={1:'F',2:'G',3:'H',4:'J',5:'K',6:'M',7:'N',8:'Q',9:'U',10:'V',11:'X',12:'Z'}
MON={1:'January',2:'February',3:'March',4:'April',5:'May',6:'June',7:'July',8:'August',9:'September',10:'October',11:'November',12:'December'}
PRODUCTS=[('C','BU'),('S','BU'),('SM','ST')]   # prefix, uom
YEARS=[(25,2025),(26,2026)]
def tmpl(code, desc, month, uom):
    row={'code':code,'description':desc,'month':month,'contract_type_id':'1','application':'both',
         'source_id_code':'M3','is_integration':'FALSE','ticker_code':'','currency':'USD','incoterm_id':'1',
         'uom':uom,'basis_port_id':'MYPKG','forward_months':'1','is_active':'TRUE'}
    return [row.get(h.strip(),'') for h in hdr]
out=[]; new=[]; kept=0
for prefix,uom in PRODUCTS:
    for yy,yyyy in YEARS:
        for m in range(1,13):
            code=f"{prefix}{LET[m]}{yy}"
            if code in existing:
                out.append(existing[code]); kept+=1
            else:
                r=tmpl(code, f"{MON[m]} {yyyy}", f"{yyyy}-{m:02d}-01", uom)
                out.append(r); new.append(code)
print(f"target rows={len(out)} (expected 72)  kept-existing={kept}  NEW={len(new)}")
for pfx,_ in PRODUCTS:
    n=[c for c in new if c.startswith(pfx) and not (pfx=='S' and c.startswith('SM'))]
    print(f"  new {pfx}: {len(n)} -> {n}")
# any existing codes NOT in the canonical 72?
canon={r[iCode] for r in out}
orphan=[c for c in existing if c not in canon]
print("  existing codes outside canonical 72 (untouched, would be DROPPED if overwrite):", orphan or "none")
if os.environ.get('GTMS_WRITE')=='1':
    with open('recon/backup/Price Index.pre-seed.csv','w',newline='') as fh:
        w=csv.writer(fh); w.writerow(hdr); w.writerows(v[1:])
    svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{TAB}'").execute()
    svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{TAB}'!A1",valueInputOption='RAW',body={'values':[hdr]+out}).execute()
    print(f"WROTE {len(out)} rows to '{TAB}'. Backup recon/backup/Price Index.pre-seed.csv")
else:
    print("(dry-run; GTMS_WRITE=1 to apply)")
