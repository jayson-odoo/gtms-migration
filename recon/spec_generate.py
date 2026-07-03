# -*- coding: utf-8 -*-
"""Generate SpecGroup + Spec Group Spec rows from the user-marked candidates -> STAGING tabs
(not live). Uses user's final_name. Flags SpecNames missing from the Specifications tab."""
import re, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'; PUR='Purchasing QL Feed  QL International - QL Master Data (Part 1) 20260629.xlsx'
TEST={'CORN','SB','SBM','SBO','DDGS','DUMMY'}
def banner(s): 
    s=str(s).upper(); return ('SDN BHD' in s or 'PTE LTD' in s or 'QL FEED' in s or 'QL INTERNATIONAL' in s)
df=pd.read_excel(f"{DIR}/{PUR}",sheet_name='SpecGroup',header=0,dtype=str).fillna('')
P='SpecGroupName2';O='SpecGroupName3 (Origin)';S='SpecGroupName4 (Seller)';D='SpecGroupDescription'
starts=[i for i in range(len(df)) if str(df.iloc[i][P]).strip() and not banner(df.iloc[i][P]) and str(df.iloc[i][P]).strip() not in TEST and str(df.iloc[i][P]).strip().upper()!='SPECGROUPNAME2']
bounds=starts+[len(df)]; blocks=[]
for a,b in zip(bounds,bounds[1:]):
    blk=df.iloc[a:b]
    desc=next((str(x).strip() for x in blk[D] if str(x).strip()),'')
    code=next((str(x).strip() for x in blk['M3 Code'] if str(x).strip()),'')
    specs=[(str(r['SpecName']).strip(),str(r['minimum']).strip(),str(r['maximum']).strip(),
            str(r['minimum_basis']).strip(),str(r['maximum_basis']).strip(),
            str(r['value_unit']).strip(),str(r['value_type']).strip())
           for _,r in blk.iterrows()
           if str(r['SpecName']).strip() and (str(r['minimum']).strip() or str(r['maximum']).strip())]
    blocks.append(dict(product=str(df.iloc[a][P]).strip(),desc=desc,code=code,specs=specs))

svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return svc.spreadsheets().values().get(spreadsheetId=SID,range=f"'{t}'").execute().get('values',[])
review=get('RECON 300626 - SpecGroup Candidates')  # row3=hdr, row4+=data (block order)
marks=review[3:]
# existing specs + spec groups
specs_tab=get('Specifications'); sh=specs_tab[0]; existing_specs={str(dict(zip(sh,r)).get('name','')).strip().upper() for r in specs_tab[1:]}
sg_tab=get('SpecGroup'); gh=sg_tab[0]; existing_groups={str(dict(zip(gh,r)).get('name','')).strip().upper() for r in sg_tab[1:]}

new_groups=[]; new_specrows=[]; missing_specs={}; dup_names=[]
for i, m in enumerate(marks):
    if i>=len(blocks): break
    add=(m[0].strip().upper() if len(m)>0 and m[0] else '')
    if not add.startswith('Y'): continue
    final=(m[1].strip() if len(m)>1 and m[1] else '') or (m[2].strip() if len(m)>2 else '')
    blk=blocks[i]
    if final.upper() in existing_groups: dup_names.append(final); continue
    new_groups.append([final, blk['desc'], blk['desc'], 'TRUE', blk['code']])
    for sn,mn,mx,mb,xb,vu,vt in blk['specs']:
        new_specrows.append([final, sn, mn, mx, mb, xb, 'FALSE'])
        if sn.upper() not in existing_specs: missing_specs.setdefault(sn,(vu,vt))

print(f"marked Y -> new spec GROUPS={len(new_groups)} | new Spec Group Spec ROWS={len(new_specrows)}")
print(f"dup names skipped (already in SpecGroup): {len(dup_names)} {dup_names[:5]}")
print(f"\nSpecNames NOT in 'Specifications' tab (would FK-fail; need adding): {len(missing_specs)}")
for s in sorted(missing_specs): print(f"    {s!r} unit={missing_specs[s][0]} type={missing_specs[s][1]}")

def write(title, header, rows, note):
    meta=svc.spreadsheets().get(spreadsheetId=SID).execute()
    if title not in [s['properties']['title'] for s in meta['sheets']]:
        svc.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute()
    svc.spreadsheets().values().clear(spreadsheetId=SID,range=f"'{title}'").execute()
    svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':[[note],[],header]+rows}).execute()
write('RECON 300626 - SpecGroup NEW', ['name','description','sales_spec_group_description','is_active','Product M3 Code'], new_groups,
      f'STAGING: {len(new_groups)} new spec groups to append to SpecGroup (review names/desc before go-live).')
write('RECON 300626 - SpecGroupSpec NEW', ['SpecGroupName2','SpecName','minimum','maximum','minimum_basis','maximum_basis','is_derived'], new_specrows,
      f'STAGING: {len(new_specrows)} Spec Group Spec lines. SpecName must exist in Specifications tab (see flagged missing).')
spec_rows=[[s, s, missing_specs[s][0], missing_specs[s][1]] for s in sorted(missing_specs)]
write('RECON 300626 - Specifications NEW', ['name','description','value_unit','value_type'], spec_rows,
      f'STAGING: {len(spec_rows)} specifications missing from Specifications tab (needed so Spec Group Spec FK resolves).')
print("\nwrote staging tabs: SpecGroup NEW, SpecGroupSpec NEW, Specifications NEW")
