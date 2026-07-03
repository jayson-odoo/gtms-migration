# -*- coding: utf-8 -*-
import re, pandas as pd
from collections import Counter
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'; PUR='Purchasing QL Feed  QL International - QL Master Data (Part 1) 20260629.xlsx'
TEST={'CORN','SB','SBM','SBO','DDGS','DUMMY'}
def banner(s): 
    s=str(s).upper(); return ('SDN BHD' in s or 'PTE LTD' in s or 'QL FEED' in s or 'QL INTERNATIONAL' in s)
def clean_origin(o):
    o=o.strip()
    if re.search(r'\(WM\)|\(EM\)',o): return ''
    if 'CONTAINER' in o.upper() or 'reserved code' in o.lower() or 'disabled in GTMS' in o: return ''
    return o
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
df=pd.read_excel(f"{DIR}/{PUR}",sheet_name='SpecGroup',header=0,dtype=str).fillna('')
P='SpecGroupName2';O='SpecGroupName3 (Origin)';S='SpecGroupName4 (Seller)';D='SpecGroupDescription'
starts=[i for i in range(len(df)) if str(df.iloc[i][P]).strip() and not banner(df.iloc[i][P]) and str(df.iloc[i][P]).strip() not in TEST and str(df.iloc[i][P]).strip().upper()!='SPECGROUPNAME2']
bounds=starts+[len(df)]; blocks=[]
for a,b in zip(bounds,bounds[1:]):
    blk=df.iloc[a:b]; prod=str(df.iloc[a][P]).strip()
    origins=sorted({clean_origin(x) for x in blk[O] if clean_origin(x)})
    reg=[]
    if blk[O].str.contains(r'\(WM\)',na=False).any(): reg.append('WEST MALAYSIA')
    if blk[O].str.contains(r'\(EM\)',na=False).any(): reg.append('EAST MALAYSIA')
    sellers=sorted({x.strip() for x in blk[S] if x.strip() and not banner(x)})
    specs=[f"{str(r['SpecName']).strip()}[{str(r['minimum']).strip()}-{str(r['maximum']).strip()}]{str(r['value_unit']).strip()}"
           for _,r in blk.iterrows() if str(r['SpecName']).strip()]
    code=next((str(x).strip() for x in blk['M3 Code'] if str(x).strip()),'')
    region=' / '.join(reg)
    origin_txt=' / '.join(origins)
    name=' '.join(x for x in [region, origin_txt, prod] if x)
    blocks.append(dict(name=name,product=prod,code=code,region=region,origins=origin_txt,
                       sellers='; '.join(sellers),n_specs=len(specs),specs=' | '.join(specs)))
# jayson existing names (fuzzy token-set)
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
jsg=svc.spreadsheets().values().get(spreadsheetId=SID,range="'SpecGroup'").execute().get('values',[])
jh=jsg[0]; jnames=[dict(zip(jh,r)).get('name','') for r in jsg[1:]]
jtok=[set(re.findall(r'[A-Z0-9]+',nk(x))) for x in jnames]  # crude
def exists(nm):
    t=set(re.findall(r'[A-Z0-9]+', re.sub(r'[^A-Z0-9 ]',' ',nm.upper())))
    for jn,js in zip(jnames, [set(re.findall(r'[A-Z0-9]+',x.upper())) for x in jnames]):
        if t and js and len(t&js)/max(1,len(t))>=0.8 and len(t&js)/max(1,len(js))>=0.6: return jn
    return ''
for blk in blocks: blk['maybe_in_jayson']=exists(blk['name'])
newn=sum(1 for b in blocks if not b['maybe_in_jayson'])
print(f"parsed blocks={len(blocks)} | maybe-already-in-Jayson={len(blocks)-newn} | candidate-NEW={newn}")
# write tab
cols=['name','product','code','region','origins','sellers','n_specs','maybe_in_jayson','specs']
title='RECON 300626 - SpecGroup Candidates'
meta=svc.spreadsheets().get(spreadsheetId=SID).execute()
if title not in [s['properties']['title'] for s in meta['sheets']]:
    svc.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
svc.spreadsheets().values().clear(spreadsheetId=SID,range=f"'{title}'").execute()
banner_txt=('PARSED candidates from raw SpecGroup (hierarchical draft; 1 block=1 candidate spec group). name=best-effort [Region][Origin][Product]; sellers listed separately. maybe_in_jayson=fuzzy match to an existing SpecGroup (blank=likely NEW). NEEDS YOUR REVIEW - nothing added. Origin col was polluted w/ packing text (dropped).')
vals=[[banner_txt],[],cols]+[[b[c] for c in cols] for b in blocks]
svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':vals}).execute()
print(f"wrote '{title}' with {len(blocks)} candidates")
