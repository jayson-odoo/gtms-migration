# -*- coding: utf-8 -*-
"""Surgical: keep Counterparty v2 structure (merges, M3 Vendor Code, Unique/Duplicate, LE, is_internal),
OVERWRITE raw-sourced fields (name/long_name/reg#/tin/type/address/country/billing/phone/etc.) from raw
Vendor/Customer by M3 Code. Recompute cleaned_name + duplicated_cleaned_name. Backup + audit."""
import re, csv, time, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; DIR='/home/src/raw_master/300626'; BK='/home/src/recon/backup'
ACC={'QLF':'Account QL Feed - Master Data (Part 1) 20260627.xlsx',
     'QLI':'Account QL International - QL Master Data (Part 1 - Trade Customer, Trade Vendor and Legal Entity) submited on 26.06.2026.xlsx'}
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def clean(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
RAWFIELDS=['name','long_name','company_registration_number','tax_registration_number','tin_no','type',
           'address','country','billing_address','billing_country','phone','fax','website','reference_1','reference_2']
# build raw lookup by M3 code (customer preferred, else vendor)
def g(r,n):
    for k in r.index:
        if k.strip().lower()==n.lower():
            v=str(r[k]).strip(); return '' if v.lower()=='nan' else v
    return ''
lookup={}
for ent,f in ACC.items():
    for side in ('Customer','Vendor'):   # customer first so it wins for merged rows keyed on customer code
        df=pd.read_excel(f"{DIR}/{f}",sheet_name=side,header=0,dtype=str).fillna('')
        for _,r in df.iterrows():
            code=clean(g(r,'M3 Code'))
            if not code: continue
            rec={fld:g(r,fld) for fld in RAWFIELDS}
            if code not in lookup: lookup[code]=rec
            else:  # fill any blanks from the other side
                for fld in RAWFIELDS:
                    if not lookup[code].get(fld) and rec.get(fld): lookup[code][fld]=rec[fld]
print("raw codes in lookup:", len(lookup))
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
v=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'").execute()).get('values',[])
h=[c.strip() for c in v[0]]; idx={c:i for i,c in enumerate(h)}
mc=idx['M3 Code']; cn=idx.get('cleaned_name'); dcn=idx.get('duplicated_cleaned_name')
with open(f"{BK}/Counterparty v2.pre-namefix.csv",'w',newline='') as f: csv.writer(f).writerows(v)
changed=[]; notfound=[]; newrows=[v[0]]
for r in v[1:]:
    r=r+['']*(len(h)-len(r)); code=clean(r[mc])
    rec=lookup.get(code)
    if not rec:
        if r[mc].strip(): notfound.append(r[mc].strip())
        newrows.append(r[:len(h)]); continue
    oldname=r[idx['name']].strip()
    for fld in RAWFIELDS:
        val=rec.get(fld,'')
        if fld=='name':
            if val: r[idx[fld]]=val
        else:
            if val: r[idx[fld]]=val   # overwrite when raw has a value; keep existing if raw blank
    if 'exist_in_countries' in idx and rec.get('country'): r[idx['exist_in_countries']]=rec['country']
    if cn is not None: r[cn]=clean(r[idx['name']])
    if r[idx['name']].strip()!=oldname: changed.append((r[mc].strip(), oldname, r[idx['name']].strip()))
    newrows.append(r[:len(h)])
# recompute duplicated_cleaned_name
if dcn is not None:
    from collections import defaultdict
    seen=defaultdict(int)
    for r in newrows[1:]:
        c=r[cn] if cn is not None else ''
        seen[c]+=1; r[dcn]='Duplicate' if seen[c]>1 else 'Unique'
print(f"rows with NAME changed = {len(changed)} (showing 20):")
for code,o,n in changed[:20]: print(f"   {code:12} {o[:30]:30} -> {n[:30]}")
print(f"CPv2 codes NOT in raw (left as-is) = {len(set(notfound))}: {sorted(set(notfound))[:15]}")
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range="'Counterparty v2'").execute())
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'Counterparty v2'!A1",valueInputOption='RAW',body={'values':newrows}).execute())
print(f"\noverwrote Counterparty v2 ({len(newrows)-1} rows, backup Counterparty v2.pre-namefix.csv)")
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 7 CPv2 names overwritten from raw 2026-07-01',f'{len(changed)} names corrected by M3 code; structure/merges kept']]}).execute())
print("audited.")
