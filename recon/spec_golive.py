# -*- coding: utf-8 -*-
"""Clean names, MERGE same-named blocks, back up + APPEND new SpecGroup / Spec Group Spec /
Specifications rows to LIVE tabs. Add-only. Cached reads + 429 retry."""
import re, csv, time, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'; PUR='Purchasing QL Feed  QL International - QL Master Data (Part 1) 20260629.xlsx'; BK='/home/src/recon/backup'
TEST={'CORN','SB','SBM','SBO','DDGS','DUMMY'}
def banner(s):
    s=str(s).upper(); return ('SDN BHD' in s or 'PTE LTD' in s or 'QL FEED' in s or 'QL INTERNATIONAL' in s)
def clean_name(s):
    s=re.sub(r'\bIN BULK\b',' ',str(s),flags=re.I).replace('/',' ')
    return re.sub(r'\s+',' ',s).strip()
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
_cache={}
def get(t):
    if t not in _cache:
        _cache[t]=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range=f"'{t}'").execute()).get('values',[])
    return _cache[t]
def backup(t,v):
    with open(f"{BK}/{t}.csv",'w',newline='') as f: csv.writer(f).writerows(v)
def appendrows(t, dicts):
    v=get(t); hdr=[h.strip() for h in v[0]]; backup(t,v); before=len(v)-1
    rows=[[d.get(h,'') for h in hdr] for d in dicts]
    retry(lambda: svc.spreadsheets().values().append(spreadsheetId=SID,range=f"'{t}'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows}).execute())
    return before, before+len(rows)

df=pd.read_excel(f"{DIR}/{PUR}",sheet_name='SpecGroup',header=0,dtype=str).fillna('')
P='SpecGroupName2';O='SpecGroupName3 (Origin)';S='SpecGroupName4 (Seller)';D='SpecGroupDescription'
hasSD='SpecDescription' in df.columns
starts=[i for i in range(len(df)) if str(df.iloc[i][P]).strip() and not banner(df.iloc[i][P]) and str(df.iloc[i][P]).strip() not in TEST and str(df.iloc[i][P]).strip().upper()!='SPECGROUPNAME2']
bounds=starts+[len(df)]; blocks=[]
for a,b in zip(bounds,bounds[1:]):
    blk=df.iloc[a:b]
    blocks.append(dict(desc=next((str(x).strip() for x in blk[D] if str(x).strip()),''),
        code=next((str(x).strip() for x in blk['M3 Code'] if str(x).strip()),''),
        specs=[(str(r['SpecName']).strip(),str(r['minimum']).strip(),str(r['maximum']).strip(),
                (str(r['SpecDescription']).strip() if hasSD else str(r['SpecName']).strip()),
                str(r['value_unit']).strip(),str(r['value_type']).strip(),
                str(r['minimum_basis']).strip(),str(r['maximum_basis']).strip())
               for _,r in blk.iterrows() if str(r['SpecName']).strip() and (str(r['minimum']).strip() or str(r['maximum']).strip())]))

marks=get('RECON 300626 - SpecGroup Candidates')[3:]
existing_groups={str(dict(zip(get('SpecGroup')[0],r)).get('name','')).strip().upper() for r in get('SpecGroup')[1:]}
existing_specs={str(dict(zip(get('Specifications')[0],r)).get('name','')).strip().upper() for r in get('Specifications')[1:]}

groups={}; conflicts=[]
for i,m in enumerate(marks):
    if i>=len(blocks): break
    if not (len(m)>0 and str(m[0]).strip().upper().startswith('Y')): continue
    name=clean_name((m[1].strip() if len(m)>1 and m[1] else '') or (m[2].strip() if len(m)>2 else ''))
    if not name or name.upper() in existing_groups: continue
    g=groups.setdefault(name, dict(desc=blocks[i]['desc'],code=blocks[i]['code'],specs={}))
    for sn,mn,mx,sd,vu,vt,mb,xb in blocks[i]['specs']:
        k=sn.upper()
        if k in g['specs'] and g['specs'][k][:2]!=(mn,mx): conflicts.append((name,sn,g['specs'][k][:2],(mn,mx)))
        g['specs'].setdefault(k,(mn,mx,sn,sd,vu,vt,mb,xb))

sg_rows=[dict(name=n,description=g['desc'],sales_spec_group_description=g['desc'],is_active='TRUE',**{'Product M3 Code':g['code']}) for n,g in groups.items()]
spec_rows=[]; allnames=set()
for n,g in groups.items():
    for k,(mn,mx,sn,sd,vu,vt,mb,xb) in g['specs'].items():
        spec_rows.append(dict(SpecGroupName2=n,SpecName=sn,SpecDescription=sd or sn,value_unit=vu,value_type=vt,minimum=mn,maximum=mx,minimum_basis=mb,maximum_basis=xb,is_derived='FALSE')); allnames.add(sn)
new_specs=[dict(name=s,description=s,value_unit='%' if s.lower()=='fibre' else '',value_type='') for s in sorted(allnames) if s.upper() not in existing_specs]

print(f"unique NEW spec groups={len(sg_rows)} | spec lines={len(spec_rows)} | new Specifications={[d['name'] for d in new_specs]}")
print(f"merge min/max conflicts (kept first): {len(conflicts)}")
for c in conflicts[:10]: print("   ",c)
print("names:"); [print("   ",r['name']) for r in sg_rows]
if new_specs: print("Specifications", appendrows('Specifications', new_specs))
print("SpecGroup", appendrows('SpecGroup', sg_rows))
print("Spec Group Spec", appendrows('Spec Group Spec', spec_rows))
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 2 SpecGroup go-live 2026-07-01',f'{len(sg_rows)} groups / {len(spec_rows)} spec lines / {len(new_specs)} specs']]}).execute())
print("backed up + audited. NOTE: SpecGroupFIP (WM/EM tiered bands) NOT generated - flag for user.")
