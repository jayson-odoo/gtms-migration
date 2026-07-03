# -*- coding: utf-8 -*-
"""Improved Part A: match Product Spec_SC raw products -> Jayson spec groups by product-token subset +
origin, OVERWRITE sales_spec_group_description. Idempotent (reads current). Report matched/unmatched."""
import io, re, csv, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; FID='12HJ4fHGWk50KeGpJW3NYV2O3pZOop_EV'; BK='/home/src/recon/backup'
creds=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/spreadsheets'])
drive=build('drive','v3',credentials=creds,cache_discovery=False); sheets=build('sheets','v4',credentials=creds,cache_discovery=False)
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def getj(t): return retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=FID)); d=False
while not d: _,d=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True)
ws=wb['Product Spec_SC']; rows=[[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]
blocks=[]; cur=None
for r in rows:
    r=r+['']*(3-len(r))
    if r[0].strip(): cur={'product':r[0].strip(),'lines':[]}; blocks.append(cur)
    elif cur is not None and (r[1].strip() or r[2].strip()): cur['lines'].append((r[1].strip()+'\t'+r[2].strip()).strip())
ORIG=['ARGENTINA','BRAZIL','US','CHINA','AUSTRALIA','PARAGUAY','CHILE','LOCAL','MALAYSIA']
def norm_orig(s):
    u=' '+re.sub(r'[^A-Z ]',' ',s.upper())+' '
    u=u.replace('BRAZILLIAN','BRAZIL').replace('BRAZILIAN','BRAZIL').replace('AUSTRALIAN','AUSTRALIA').replace('UNITED STATES','US').replace(' U S ',' US ')
    for o in ORIG:
        if ' '+o+' ' in u: return o
    return ''
STOP=set(ORIG)|{'YELLOW','STEAM','DRIED','EXPORT','TVBN','HSC','LH','GM','COMPANY','ASIA','PTE','LTD','SDN','BHD','INC','LLC','SA','S','A','OF','AMERICA','THE','GRAIN','GRAINS','NO','OR','BETTER','GEN','PURPOSE','WITH','MOLD','INHIBITOR','BRAZILLIAN','BRAZILIAN','AUSTRALIAN','UNITED','STATES','U','HPRO','HIPRO','PRO','SPEC','PROTEIN','WEST','EAST','IND','VN'}
KEEP_NUM={'55','60','63','65','67','100','90','150'}
def toks(s):
    t=s.upper().replace('H-PRO',' ').replace('HI-PRO',' ').replace('SOYABEAN','SOYA BEAN').replace('DDGS','DISTILLERS')
    t=re.sub(r'\bL-?MET\b','METHIONINE',t)
    u=re.sub(r'[^A-Z0-9 ]',' ',t)
    out=set()
    for w in u.split():
        if w in STOP: continue
        if w.isdigit() and w not in KEEP_NUM: continue
        if len(w)>1 or w.isdigit(): out.add(w)
    return out
sg=getj('SpecGroup'); sh=[x.strip() for x in sg[0]]; ni=sh.index('name'); sdi=sh.index('sales_spec_group_description')
def colA1(i):
    s=''; i+=1
    while i: i,r=divmod(i-1,26); s=chr(65+r)+s
    return s
raws=[(b, toks(b['product']), norm_orig(b['product'])) for b in blocks]
updates=[]; applied=defaultdict(list); matched_raw=set()
for ri,r in enumerate(sg[1:],start=2):
    nm=r[ni].strip() if len(r)>ni else ''
    if not nm: continue
    gt=toks(nm); go=norm_orig(nm)
    best=None
    for b,rt,ro in raws:
        if not rt: continue
        if rt <= gt and (ro==go or ro=='' or (ro=='LOCAL' and 'LOCAL' in nm.upper())):
            if best is None or len(rt)>len(best[1]): best=(b,rt,ro)
    if best:
        b=best[0]; text='\n'.join(b['lines'])
        updates.append({'range':f"'SpecGroup'!{colA1(sdi)}{ri}",'values':[[text]]})
        applied[b['product']].append(nm); matched_raw.add(b['product'])
print(f"raw products matched={len(matched_raw)}/{len(blocks)} | spec group cells to overwrite={len(updates)}")
for p,gs in applied.items(): print(f"   '{p}' -> {len(gs)} groups")
print("STILL unmatched:", sorted(b['product'] for b in blocks if b['product'] not in matched_raw))
with open(f"{BK}/SpecGroup.pre-salesdesc2.csv",'w',newline='') as f: csv.writer(f).writerows(sg)
if updates: retry(lambda: sheets.spreadsheets().values().batchUpdate(spreadsheetId=JAY,body={'valueInputOption':'RAW','data':updates}).execute())
print(f"overwrote {len(updates)} cells (backup SpecGroup.pre-salesdesc2.csv)")
