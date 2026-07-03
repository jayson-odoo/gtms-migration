# -*- coding: utf-8 -*-
"""Read-only reconciliation: dept-submitted raw xlsx (raw_master/300626) vs Jayson sheet tabs.
Identifies, per entity & per source file: rows ADDED (in raw, key absent in Jayson),
MISSING_IN_RAW (in Jayson, key absent in raw - informational), CHANGED (field differs).
Writes per-entity CSVs to recon/out/ and prints a summary. Does NOT modify any data tab."""
import os, re, glob
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'
OUT='/home/src/recon/out'
os.makedirs(OUT, exist_ok=True)

ACC_QLF='Account QL Feed - Master Data (Part 1) 20260627.xlsx'
ACC_QLI='Account QL International - QL Master Data (Part 1 - Trade Customer, Trade Vendor and Legal Entity) submited on 26.06.2026.xlsx'
ACC_PUTR='Account QL International & QL Feed - QL Master Data (Packing Unit, Trader, Payment Term, Payment Method) submited on 26.06.2026.xlsx'
PUR_P1='Purchasing QL Feed  QL International - QL Master Data (Part 1) 20260629.xlsx'
PUR_PUTR='Purchasing QL Feed  QL International - QL Master Data (Packing Unit Trader Payment Term) 20260629.xlsx'
SALES='Sales QLI & QLF - GTMS_INVENTORY LOCATION_290626.xlsx'
SHIP='Shipping QLI & QLF - Master Data Port.xlsx'
USERS='GTMS - User ID List.xlsx'

def short(f): return f.split(' - ')[0][:22] if ' - ' in f else f[:22]

# ---------- helpers ----------
def norm(v, mode='exact'):
    if v is None: return ''
    s=str(v).strip()
    if s.lower() in ('nan','none','nat'): return ''
    s=re.sub(r'\s+',' ',s)
    if mode=='upper': return s.upper()
    if mode=='ci': return s.casefold()
    if mode=='num':
        try: return ('%g'%float(s.replace(',','')))
        except: return s.casefold()
    if mode=='pct':
        # raw stores fractions (0.05) where Jayson stores percent (5); normalise to percent
        try:
            f=float(s.replace('%','').replace(',',''))
            if f<1 and f!=0: f=f*100
            return '%g'%f
        except: return s.casefold()
    return s

def load_raw(file, sheet, header):
    df=pd.read_excel(os.path.join(DIR,file), sheet_name=sheet, header=header, dtype=str)
    df=df.dropna(how='all')
    df.columns=[str(c).strip() for c in df.columns]
    return df

def load_jayson(svc, tab):
    vr=svc.spreadsheets().values().get(spreadsheetId=SID, range=f"'{tab}'").execute()
    vals=vr.get('values',[])
    if not vals: return pd.DataFrame()
    hdr=[str(c).strip() for c in vals[0]]
    rows=vals[1:]
    width=len(hdr)
    norm_rows=[(r+['']*width)[:width] for r in rows]
    df=pd.DataFrame(norm_rows, columns=hdr)
    df=df.loc[:, ~pd.Index(df.columns).duplicated()]  # drop dup header cols
    return df

# ---------- entity configs ----------
# fields: list of (raw_col, jayson_col, mode)
E=[
 dict(entity='Countries', tab='Countries', keyr='code / M3 Code', keyj='code', keymode='upper',
      fields=[('name','name','ci')],
      sources=[(ACC_QLF,'Countries',1)]),
 dict(entity='UoM', tab='UoM', keyr='code / M3 Code', keyj='code', keymode='upper',
      fields=[('description','description','ci')],
      sources=[(ACC_QLF,'UoM',1)]),
 dict(entity='States', tab='States', keyr='__concat__', keyj='concat', keymode='upper',
      fields=[], concat_raw=('country','name'),
      sources=[(ACC_QLF,'States',1)]),
 dict(entity='Tax', tab='Tax', keyr='M3 Code', keyj='code', keymode='upper',
      fields=[('Name','name','ci'),('Short Description','short_description','ci'),
              ('Contract Description','contract_description','ci'),
              ('Transaction Type','transaction_type','ci'),('Percentage','percentage','pct')],
      sources=[(ACC_QLF,'Tax',1)]),
 dict(entity='Legal Entity', tab='Legal Entity', keyr='code', keyj='code', keymode='upper',
      fields=[('name','name','ci'),('short_name','short_name','ci'),('currency','currency','ci'),
              ('company_registration_number','company_registration_number','ci'),
              ('tin_number','tin_number','ci'),('country','country','ci')],
      sources=[(ACC_QLF,'Legal Entity',0),(ACC_QLI,'Legal Entity',0)]),
 dict(entity='Profit Centers', tab='Profit Centers', keyr='M3 Code', keyj='code', keymode='upper',
      fields=[('name','name','ci'),('long_name','long_name','ci')],
      sources=[(ACC_QLF,'Profit Centers',0)]),
 dict(entity='Vendor', tab='Vendor', keyr='M3 Code', keyj='M3 Code', keymode='upper',
      fields=[('name','name','ci'),('long_name','long_name','ci'),('type','type','ci'),
              ('legal_entity','legal_entity','ci'),('country','country','ci'),
              ('tin_no','tin_no','ci')],
      sources=[(ACC_QLF,'Vendor',0),(ACC_QLI,'Vendor',0),(PUR_P1,'Vendor',0)]),
 dict(entity='Customer', tab='Customer', keyr='M3 Code', keyj='M3 Code', keymode='upper',
      fields=[('name','name','ci'),('long_name','long_name','ci'),('type','type','ci'),
              ('legal_entity','legal_entity','ci'),('country','country','ci'),
              ('tin_no','tin_no','ci')],
      sources=[(ACC_QLF,'Customer',0),(ACC_QLI,'Customer',0),(PUR_P1,'Customer',0)]),
 dict(entity='Products', tab='Products', keyr='M3 Code', keyj='code', keymode='upper',
      fields=[('contract_number_reference','contract_number_reference','ci'),
              ('description','description','ci'),('packing_unit','packing_unit','ci'),
              ('default_uom','default_uom','ci'),('hs_code','hs_code','ci')],
      sources=[(PUR_P1,'Products',0),(ACC_QLF,'Products',0)]),
 dict(entity='Ports', tab='Ports', keyr='code', keyj='code', keymode='upper',
      fields=[('name','name','ci'),('short_name','short_name','ci'),('country','country','ci'),
              ('state','state','ci'),('region','region','ci')],
      sources=[(SHIP,'Ports',0)]),
 dict(entity='Inventory Locations', tab='Inventory Locations', keyr='code', keyj='code', keymode='upper',
      fields=[('name','name','ci'),('short_name','short_name','ci'),('location_type','location_type','ci')],
      sources=[(SHIP,'Inventory Location',0)]),
 dict(entity='Inventory Locations', tab='Inventory Locations', keyr='M3 Code', keyj='code', keymode='upper',
      fields=[('name','name','ci'),('short_name','short_name','ci'),('Location Type','location_type','ci')],
      sources=[(SALES,'Inventory Locations_QLF_29.6.26',0),(SALES,'Inventory Locations_QLI_29.6.26',0)]),
 dict(entity='Packing Unit', tab='Packing Unit', keyr='code', keyj='original_code', keymode='upper',
      fields=[('description','description','ci')],
      sources=[(ACC_PUTR,'Packing Unit',0),(PUR_PUTR,'Packing Unit',0)]),
 dict(entity='Trader (Salesperson)', tab='Trader (Salesperson)', keyr='code', keyj='code', keymode='upper',
      fields=[('name','name','ci')],
      sources=[(ACC_PUTR,'Trader (Salesperson)',0),(PUR_PUTR,'Trader (Salesperson)',0)]),
 dict(entity='Payment Term', tab='Payment Term', keyr='M3 Code', keyj='id', keymode='upper',
      fields=[('M3 Description','name','ci'),('contract_description','contract_description','ci'),
              ('invoice_description','invoice_description','ci'),('due_date_days','due_date_days','num'),
              ('payment_mode','payment_mode','ci'),('lc_type','lc_type','ci')],
      sources=[(ACC_PUTR,'Payment Term',0),(PUR_PUTR,'Payment Term',0)]),
 dict(entity='Users', tab='Users', keyr='Code', keyj='code', keymode='upper',
      fields=[('Name','name','ci'),('Email','email','ci')],
      sources=[(USERS,'Sheet1',0)]),
]

creds=Credentials.from_service_account_file(KEY, scopes=['https://www.googleapis.com/auth/spreadsheets'])
svc=build('sheets','v4',credentials=creds,cache_discovery=False)

jcache={}
def jayson(tab):
    if tab not in jcache: jcache[tab]=load_jayson(svc, tab)
    return jcache[tab]

summary=[]
all_rows=[]
for cfg in E:
    jdf=jayson(cfg['tab'])
    jkey=cfg['keyj']
    if jkey not in jdf.columns:
        print(f"!! {cfg['entity']}: jayson key col '{jkey}' missing in tab '{cfg['tab']}' cols={list(jdf.columns)[:8]}")
        continue
    # jayson index
    jmap={}; jdup=0
    for _,row in jdf.iterrows():
        k=norm(row.get(jkey,''), cfg['keymode'])
        if not k: continue
        if k in jmap: jdup+=1
        else: jmap[k]=row
    for (file,sheet,hdr) in cfg['sources']:
        try:
            rdf=load_raw(file,sheet,hdr)
        except Exception as ex:
            print(f"!! load {sheet}<-{short(file)}: {ex}"); continue
        src=f"{short(file)}::{sheet}"
        added=changed=matched=rdup=missingkey=0
        seen=set()
        for _,row in rdf.iterrows():
            if cfg['keyr']=='__concat__':
                a,b=cfg['concat_raw']
                kraw=norm(row.get(a,''),'upper')+norm(row.get(b,''),'upper')
            else:
                if cfg['keyr'] not in rdf.columns: kraw=''
                else: kraw=norm(row.get(cfg['keyr'],''), cfg['keymode'])
            if not kraw:
                missingkey+=1; continue
            if kraw in seen: rdup+=1; continue
            seen.add(kraw)
            namev = norm(row.get('name', row.get('Name','')))
            if kraw not in jmap:
                added+=1
                all_rows.append([cfg['entity'],src,kraw,namev,'ADDED','', '', ''])
            else:
                matched+=1
                jrow=jmap[kraw]
                for (rc,jc,mode) in cfg['fields']:
                    if rc not in rdf.columns or jc not in jdf.columns: continue
                    rv=norm(row.get(rc,''),mode); jv=norm(jrow.get(jc,''),mode)
                    if not rv: continue   # raw blank -> not a change to push into Jayson
                    if rv!=jv:
                        changed+=1
                        all_rows.append([cfg['entity'],src,kraw,namev,'CHANGED',jc,
                                         str(row.get(rc,'')).strip(), str(jrow.get(jc,'')).strip()])
        # missing in raw (jayson keys not seen by THIS source)
        miss=sum(1 for k in jmap if k not in seen)
        summary.append(dict(entity=cfg['entity'],source=src,raw_rows=len(rdf),jayson_rows=len(jmap),
                            added=added,changed=changed,matched=matched,missing_in_raw=miss,
                            raw_dupkeys=rdup,blankkey=missingkey,jayson_dupkeys=jdup))

rep=pd.DataFrame(all_rows, columns=['entity','source','key','name','type','field','raw_value','jayson_value'])
rep.to_csv(f"{OUT}/discrepancies.csv", index=False)
sm=pd.DataFrame(summary)
sm.to_csv(f"{OUT}/summary.csv", index=False)
pd.set_option('display.max_rows',200); pd.set_option('display.width',200)
print(sm.to_string(index=False))
print(f"\nTotal discrepancy rows: {len(rep)}  (added={sum(rep.type=='ADDED')}, changed={sum(rep.type=='CHANGED')})")
