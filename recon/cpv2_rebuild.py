# -*- coding: utf-8 -*-
"""Rebuild Counterparty v2 from raw Vendor/Customer (QLF+QLI) by M3 code, re-applying vendor<->customer
merge (by legal_entity+cleaned_name) + dedup. Writes STAGING tab 'RECON 300626 - CPv2 REBUILD' for review
(does NOT overwrite live). Reports diff vs current."""
import re, time, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; DIR='/home/src/raw_master/300626'
ACC={'QLF':'Account QL Feed - Master Data (Part 1) 20260627.xlsx',
     'QLI':'Account QL International - QL Master Data (Part 1 - Trade Customer, Trade Vendor and Legal Entity) submited on 26.06.2026.xlsx'}
LE={'QLF':'QL Feed Sdn. Bhd.','QLI':'QL International Pte Ltd'}
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def g(r,*names):
    for n in names:
        for k in r.index:
            if k.strip().lower()==n.lower(): 
                v=str(r[k]).strip(); 
                if v and v.lower()!='nan': return v
    return ''
def clean(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
hdr=[h.strip() for h in retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range="'Counterparty v2'!1:1").execute())['values'][0]]

# collect raw entries
entries=[]  # dict per raw row
for ent,f in ACC.items():
    for side in ('Vendor','Customer'):
        df=pd.read_excel(f"{DIR}/{f}",sheet_name=side,header=0,dtype=str).fillna('')
        for _,r in df.iterrows():
            code=g(r,'M3 Code')
            if not code: continue
            entries.append(dict(side=side, code=code, ent=ent, name=g(r,'name'), long_name=g(r,'long_name'),
                le=LE[ent], company_registration_number=g(r,'company_registration_number'),
                tax_registration_number=g(r,'tax_registration_number'), tin_no=g(r,'tin_no'),
                type=g(r,'type'), address=g(r,'address'), country=g(r,'country'),
                billing_address=g(r,'billing_address'), billing_country=g(r,'billing_country'),
                phone=g(r,'phone'), fax=g(r,'fax'), website=g(r,'website'),
                reference_1=g(r,'reference_1'), reference_2=g(r,'reference_2')))
print(f"raw entries: {len(entries)} (Vendor+Customer across QLF+QLI)")

# group by (le, cleaned_name) -> merge vendor<->customer
from collections import defaultdict
groups=defaultdict(list)
for e in entries: groups[(e['ent'], clean(e['name']))].append(e)
rows=[]
for (ent,cname), es in groups.items():
    vends=[e for e in es if e['side']=='Vendor']; custs=[e for e in es if e['side']=='Customer']
    # pair customers with vendors (merge); leftovers stand alone
    n=max(len(vends),len(custs),1)
    for i in range(max(len(vends),len(custs))):
        cust=custs[i] if i<len(custs) else None; vend=vends[i] if i<len(vends) else None
        base=cust or vend
        is_v='TRUE' if vend else ''; is_c='TRUE' if cust else ''
        primary='Customer' if cust else 'Vendor'
        m3=(cust or vend)['code']
        m3vendmerge=vend['code'] if (cust and vend) else ''
        d={c:'' for c in hdr}
        d.update({'Vendor / Customer':primary,'Is Vendor':is_v,'Is Customer':is_c,'M3 Code':m3,
          'M3 Vendor Code (for merged vendor & customer)':m3vendmerge,
          'M3 code + Vendor / Customer':primary+m3,'Unique / Duplicate':'Unique',
          'cleaned_name':cname,'name':base['name'],'long_name':base['long_name'] or base['name'],
          'legal_entity_id':base['le'],'company_registration_number':base['company_registration_number'],
          'tax_registration_number':base['tax_registration_number'],'tin_no':base['tin_no'],
          'type':base['type'],'address':base['address'],'country':base['country'],
          'exist_in_countries':base['country'],'billing_address':base['billing_address'],
          'billing_country':base['billing_country'],'phone':base['phone'],'fax':base['fax'],
          'website':base['website'],'reference_1':base['reference_1'],'reference_2':base['reference_2'],
          'is_internal':'FALSE','is_active':'TRUE'})
        rows.append(d)
# duplicated_cleaned_name: mark 2nd+ occurrence of a cleaned_name (across all) as Duplicate
seen=defaultdict(int)
for d in rows:
    seen[d['cleaned_name']]+=1
    d['duplicated_cleaned_name']='Duplicate' if seen[d['cleaned_name']]>1 else 'Unique'
merged=sum(1 for d in rows if d['Is Vendor']=='TRUE' and d['Is Customer']=='TRUE')
print(f"rebuilt rows={len(rows)} | merged(V&C)={merged} | vendor-only={sum(1 for d in rows if d['Is Vendor']=='TRUE' and d['Is Customer']!='TRUE')} | customer-only={sum(1 for d in rows if d['Is Customer']=='TRUE' and d['Is Vendor']!='TRUE')}")
print(f"duplicated_cleaned_name=Duplicate: {sum(1 for d in rows if d['duplicated_cleaned_name']=='Duplicate')}")
# LIAN sanity
print("\nLIAN* / QQLLP rebuilt rows:")
for d in rows:
    if 'LIAN' in d['name'].upper() or d['M3 Code'].startswith('QQLLP') or d['M3 Code'].startswith('QLIAN'):
        print(f"   {d['M3 Code']:12} {d['Vendor / Customer']:9} {d['name'][:34]:34} dup={d['duplicated_cleaned_name']}")
# write staging
title='RECON 300626 - CPv2 REBUILD'
meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=JAY).execute())
if title not in [s['properties']['title'] for s in meta['sheets']]:
    retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
note=[[f'STAGING rebuild of Counterparty v2 from raw Vendor/Customer (QLF+QLI) by M3 code. {len(rows)} rows (current live=445). Review, esp. merges + names, before overwriting live.']]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':note+[[]]+[hdr]+[[d[c] for c in hdr] for d in rows]}).execute())
print(f"\nwrote staging '{title}' ({len(rows)} rows)")
