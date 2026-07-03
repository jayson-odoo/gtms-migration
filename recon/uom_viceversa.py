# -*- coding: utf-8 -*-
"""Add missing vice-versa (reverse-direction) rows to the 'Product UoM Conversion' Jayson tab.
For every (code, From UoM, To UoM) row, ensure (code, To UoM, From UoM) exists; if not, add it
with multiplier = 1/original (exact inverse -> guarantees round-trip). Reports reciprocal
anomalies (existing reverse whose multiplier isn't ~1/forward) WITHOUT changing them. Backs up first.
Set GTMS_WRITE=1 to actually write; default = dry report."""
import os, csv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY=os.environ['GOOGLE_APPLICATION_CREDENTIALS']; JAY=os.environ['GSHEET_ID']; TAB='Product UoM Conversion'
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{TAB}'").execute().get('values',[])
hdr=v[0]; rows=[ (r+['']*(len(hdr)-len(r)))[:len(hdr)] for r in v[1:] if any(str(x).strip() for x in r)]
iC,iF,iT,iM = hdr.index('code'),hdr.index('From UoM'),hdr.index('To UoM'),hdr.index('multiplier')
def num(s):
    try: return float(str(s).strip())
    except: return None
present={ (str(r[iC]).strip(), str(r[iF]).strip(), str(r[iT]).strip()) for r in rows }
fwd={ (str(r[iC]).strip(), str(r[iF]).strip(), str(r[iT]).strip()): num(r[iM]) for r in rows }
def fmt(x): return (f"{x:.6f}").rstrip('0').rstrip('.')
missing=[]; anomalies=[]
for r in rows:
    c,f,t,m = str(r[iC]).strip(),str(r[iF]).strip(),str(r[iT]).strip(),num(r[iM])
    rk=(c,t,f)
    if rk not in present:
        nr=list(r); nr[iF],nr[iT]=t,f
        nr[iM]= fmt(1.0/m) if m else ''
        missing.append(nr)
    else:
        rm=fwd.get(rk)
        if m and rm and abs(m*rm-1.0)>0.02:  # existing reverse is not ~reciprocal
            anomalies.append((c,f,t,m,rm))
# fix MT-anchored reciprocal errors: trust MT->U, recompute U->MT = 1/(MT->U)
mt_fwd={ (str(r[iC]).strip(), str(r[iT]).strip()): num(r[iM])
         for r in rows if str(r[iF]).strip().upper()=='MT' }
fixes=[]
for r in rows:
    c,f,t,m = str(r[iC]).strip(),str(r[iF]).strip(),str(r[iT]).strip(),num(r[iM])
    if t.upper()=='MT' and (c,f) in mt_fwd:
        mtu=mt_fwd[(c,f)]
        if mtu and m and abs(m*mtu-1.0)>0.02:
            newv=fmt(1.0/mtu); fixes.append((c,f,t,r[iM],newv)); r[iM]=newv
print("ROWS:",len(rows),"  MISSING reverses to ADD:",len(missing))
for nr in missing: print("  ADD:", [nr[iC],nr[iF],nr[iT],nr[iM]])
print(f"RECIPROCAL FIXES (recomputed X->MT = 1/(MT->X)): {len(fixes)}")
for c,f,t,old,new in fixes: print(f"  FIX {c}: {f}->{t}  {old} -> {new}")
if os.environ.get('GTMS_WRITE')=='1' and (missing or fixes):
    with open('recon/backup/Product UoM Conversion.pre-viceversa.csv','w',newline='') as fh:
        w=csv.writer(fh); w.writerow(hdr); w.writerows(rows)
    body=[hdr]+rows+missing
    svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{TAB}'").execute()
    svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{TAB}'!A1",valueInputOption='RAW',body={'values':body}).execute()
    print(f"WROTE: {len(rows)}+{len(missing)}={len(rows)+len(missing)} data rows. Backup saved.")
else:
    print("(dry-run; set GTMS_WRITE=1 to apply)")
