# -*- coding: utf-8 -*-
"""Build SpecGroup + Spec Group Spec for raw products that have no Jayson spec group (LOCAL/DDGS etc.).
One group per product (name=product desc), spec lines from the raw block. Append + backup + audit."""
import io, re, csv, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; PUR='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'; BK='/home/src/recon/backup'
creds=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/spreadsheets'])
drive=build('drive','v3',credentials=creds,cache_discovery=False); sheets=build('sheets','v4',credentials=creds,cache_discovery=False)
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def banner(s): u=str(s).upper(); return 'SDN BHD' in u or 'PTE LTD' in u or 'QL FEED' in u or 'QL INTERNATIONAL' in u
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=PUR)); d=False
while not d: _,d=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True); ws=wb['SpecGroup']
R=[[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]
h=[norm(x) for x in R[0]]
P=h.index('SpecGroupName2'); O=h.index('SpecGroupName3 (Origin)'); Dsc=h.index('SpecGroupDescription')
SN=h.index('SpecName'); MN=h.index('minimum'); MX=h.index('maximum')
MB=h.index('minimum_basis') if 'minimum_basis' in h else None; XB=h.index('maximum_basis') if 'maximum_basis' in h else None
VU=h.index('value_unit') if 'value_unit' in h else None
blocks=[]; cur=None
for row in R[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p): cur={'product':p,'origin':'','desc':'','specs':[]}; blocks.append(cur)
    if cur is None: continue
    if not cur['origin'] and row[O].strip() and not banner(row[O]): cur['origin']=row[O].strip()
    if not cur['desc'] and row[Dsc].strip(): cur['desc']=row[Dsc].strip()
    sn=row[SN].strip()
    if sn and (row[MN].strip() or row[MX].strip()):
        cur['specs'].append((sn,row[MN].strip(),row[MX].strip(),
                             row[MB].strip() if MB is not None else '', row[XB].strip() if XB is not None else '',
                             row[VU].strip() if VU is not None else ''))
# target products = those with no Jayson spec group; pick FIRST block per product; skip packing/DMX
TARGETS={'DISTILLERS DRIED GRAINS  SOLUBLES','LOCAL RICE BRAN','LOCAL FEED FLOUR','LOCAL BREAD MEAL',
         'HI PRO LOCAL SOYA BEAN MEAL','HI-PRO DISTILLERS DRIED GRAIN WITH SOLUBLES'}
jsg=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroup'").execute()).get('values',[])
jgh=[norm(x) for x in jsg[0]]; jexist={nk(r[jgh.index('name')]) for r in jsg[1:] if len(r)>1 and r[1].strip()}
jspec=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'Spec Group Spec'").execute()).get('values',[])
jsph=[norm(x) for x in jspec[0]]
jsp_names=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'Specifications'").execute()).get('values',[])
jspec_set={nk(r[0]) for r in jsp_names[1:] if r and r[0].strip()}
seen=set(); new_groups=[]; new_specrows=[]; new_specifications=set()
for b in blocks:
    if b['product'] not in TARGETS or nk(b['product']) in seen: continue
    seen.add(nk(b['product']))
    name=b['product'].strip()
    if nk(name) in jexist: continue
    new_groups.append(dict(name=name, description=b['desc'] or name, sales_spec_group_description=b['desc'] or name, is_active='TRUE'))
    for sn,mn,mx,mb,xb,vu in b['specs']:
        new_specrows.append(dict(SpecGroupName2=name, SpecName=sn, minimum=mn, maximum=mx, minimum_basis=mb, maximum_basis=xb, is_derived='FALSE'))
        if nk(sn) not in jspec_set: new_specifications.add((sn,vu))
print(f"new spec GROUPS={len(new_groups)}:")
for g in new_groups: print("   -",g['name'])
print(f"new Spec Group Spec rows={len(new_specrows)} | new Specifications={[s[0] for s in new_specifications]}")
# append Specifications first (FK), then SpecGroup, then Spec Group Spec
def appendtab(tab, hdr, dicts, bkname):
    v=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{tab}'").execute()).get('values',[])
    with open(f"{BK}/{bkname}",'w',newline='') as f: csv.writer(f).writerows(v)
    H=[norm(x) for x in v[0]]
    out=[[d.get(x,'') for x in H] for d in dicts]
    if out: retry(lambda: sheets.spreadsheets().values().append(spreadsheetId=JAY,range=f"'{tab}'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':out}).execute())
    return len(v)-1, len(v)-1+len(out)
if new_specifications:
    sp=[dict(name=n,description=n,value_unit=(vu or ''),value_type='number') for n,vu in new_specifications]
    print("Specifications", appendtab('Specifications',None,sp,'Specifications.pre-sgadd.csv'))
print("SpecGroup", appendtab('SpecGroup',None,new_groups,'SpecGroup.pre-sgadd.csv'))
print("Spec Group Spec", appendtab('Spec Group Spec',None,new_specrows,'Spec Group Spec.pre-sgadd.csv'))
cur=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 4 SpecGroup gaps add 2026-07-01',f'{len(new_groups)} groups / {len(new_specrows)} spec lines']]}).execute())
print("audited.")
