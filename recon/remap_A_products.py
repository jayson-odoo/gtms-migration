# -*- coding: utf-8 -*-
"""PHASE 1 STEP A: rebuild Jayson 'Products' = 39 generic raw master. Persist old->new mapping to
recon/out/product_map.json for junction steps. Carry packing/uom from existing Jayson rows where the
generic code already exists; else derive from raw (informal packing word -> master code). Backup + audit."""
import re, io, csv, json, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
RAW_ID='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
TEST={'CORN','SB','SBM','SBO','DDGS','DUMMY'}
ORIGIN_WORDS=['ARGENTINA','ARGENTINE','BRAZILIAN','BRAZIL','BRZ','INDIAN','INDIA','PAKISTAN','PAKISTANI','THAI','CHINESE','CHINA','USA','US','CANADIAN','CANADA','AUSTRALIAN','AUSTRALIA','UKRAINIAN','UKRAINE','MOLDOVA','PARAGUAYAN','PARAGUAY','LOCAL','MALAYSIA','MAL','CHILE','GEN.PURPOSE','GENERAL PURPOSE']
# informal raw packing word -> GTMS master packing_unit code (user-confirmed convention)
PACK={'BAG':'50KG_PP','TOTES':'TOTE_20FT_C','TOTE':'TOTE_20FT_C','DRUM':'SD_40FT_C','BULK':'BULK',
      'JUMBO':'JUMBO','25KG':'25KG_PP','50KG':'50KG_PP'}
OVR={'TGQHDDG':'TGQDDG','TGQHDDGL':'TGQDDGL','TGQHWGAU':'TGQWG','TGQHWGM':'TGQWG','TGQHWGP':'TGQWG',
     'TGQHWGU':'TGQWG','TGQHWGUS':'TGQWG','TGQHSBAH':'TGQSBM','TGQHSBPHP':'TGQSBM','TGQHSBBH':'TGQSBM',
     'TGQHSBUSHP':'TGQSBM','TGQHSBLH':'TGQSBMHPL','TGQHSBUS':'TGQSB'}
DROP={'PMQHBAG','TGQHDDGH','TGQHLME','TGQHMDCP','TGQHOTMT','TGQHDMX7'}  # +TGQHDMX7 per user
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def banner(s):
    u=str(s).upper(); return ('SDN BHD' in u or 'PTE LTD' in u or 'QL FEED' in u or 'QL INTERNATIONAL' in u)
def notinuse(s): return 'NOT IN USE' in str(s).upper() or 'DISCONTINUED' in str(s).upper()
def base(desc):
    u=re.sub(r'\([^)]*\)',' ',str(desc).upper())
    for w in ORIGIN_WORDS: u=re.sub(r'\b'+re.escape(w)+r'\b',' ',u)
    u=u.replace('NO.2','').replace('NO. 2','').replace('OR BETTER','').replace('YELLOW','')
    return re.sub(r'[^A-Z0-9]','',u)
def mappack(word):
    w=re.sub(r'[^A-Z0-9]','',str(word).upper())
    for k,v in PACK.items():
        if k in w: return v
    return ''
creds=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/spreadsheets'])
drive=build('drive','v3',credentials=creds,cache_discovery=False); sheets=build('sheets','v4',credentials=creds,cache_discovery=False)
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=RAW_ID))
done=False
while not done: _,done=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True); ws=wb['Products']
rows=list(ws.iter_rows(min_row=1)); hdr=[str(c.value).strip() if c.value is not None else '' for c in rows[0]]
mi=hdr.index('M3 Code'); di=hdr.index('description'); pi=hdr.index('packing_unit'); ui=hdr.index('default_uom')
hi=hdr.index('hs_code') if 'hs_code' in hdr else None; ci=hdr.index('contract_number_reference') if 'contract_number_reference' in hdr else None
raw={}
for r in rows[1:]:
    code=r[mi].value if len(r)>mi else None
    if not code or not str(code).strip(): continue
    c=str(code).strip()
    if c in TEST or banner(c): continue
    d=str(r[di].value).strip() if len(r)>di and r[di].value else ''
    rec=dict(desc=d, pack=(str(r[pi].value).strip() if len(r)>pi and r[pi].value else ''),
             uom=(str(r[ui].value).strip() if len(r)>ui and r[ui].value else ''),
             hs=(str(r[hi].value).strip() if hi is not None and len(r)>hi and r[hi].value else ''),
             cnr=(str(r[ci].value).strip() if ci is not None and len(r)>ci and r[ci].value else ''))
    if c not in raw or (notinuse(raw[c]['desc']) and not notinuse(d)): raw[c]=rec
raw_by_base=defaultdict(list)
for c,rec in raw.items(): raw_by_base[base(rec['desc'])].append(c)

# Jayson products - read ORIGINAL from backup so this step is idempotent (live tab may already be rewritten)
import os
bkf=f"{BK}/Products.pre-remaster.csv"
if os.path.exists(bkf):
    with open(bkf) as f: jv=list(csv.reader(f))
else:
    jv=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'Products'").execute()).get('values',[])
    with open(bkf,'w',newline='') as f: csv.writer(f).writerows(jv)
jh=[c.strip() for c in jv[0]]
def jidx(n): return jh.index(n)
jrows=[dict(zip(jh, r+['']*(len(jh)-len(r)))) for r in jv[1:] if len(r)>0 and (r[jidx('code')].strip() if len(r)>jidx('code') else '')]
jbycode={d['code'].strip():d for d in jrows}

# BUILD MAPPING old->new
mapping={}; dropped=[]
for d in jrows:
    jc=d['code'].strip()
    if jc in DROP: dropped.append(jc); continue
    if jc in OVR: mapping[jc]=OVR[jc]; continue
    if jc in raw: mapping[jc]=jc; continue
    cands=raw_by_base.get(base(d['description']),[])
    if len(cands)==1: mapping[jc]=cands[0]
    else: mapping[jc]=jc  # fallback keep (should not happen after overrides)
# final generic product set = distinct mapped targets
targets=sorted(set(mapping.values()))
json.dump({'mapping':mapping,'dropped':dropped,'targets':targets}, open('/home/src/recon/out/product_map.json','w'), indent=1)
print(f"mapping: {len(mapping)} kept-jayson-codes -> {len(targets)} generic targets | dropped {len(dropped)}: {dropped}")

# sources per target (Jayson rows collapsing into it)
src_of=defaultdict(list)
for jc,t in mapping.items():
    if jc in jbycode: src_of[t].append(jbycode[jc])
def pick_src(t):
    lst=src_of.get(t,[])
    if not lst: return None
    for d in lst:                          # prefer the row whose code == target
        if d['code'].strip()==t: return d
    for d in lst:                          # else a source that has a packing unit
        if d.get('GTMS Packing Unit','').strip(): return d
    return lst[0]
def pick_cat(t):                           # category is NOT NULL in DB: resolve from any source, else default
    for d in ([jbycode.get(t)] if t in jbycode else []) + src_of.get(t,[]):
        if d and d.get('category','').strip(): return d['category'].strip()
    return 'Non-Trade' if t.startswith('PMQ') else 'Trade'
# BUILD final Products rows (one per generic target)
PHDR=jh; puc='GTMS Packing Unit'
final=[]; newcodes=[]; unmapped_pack=[]
for t in targets:
    if t in jbycode:                       # generic code already a Jayson row -> keep curated values
        row=dict(jbycode[t])
        if not row.get('category','').strip(): row['category']=pick_cat(t)  # backfill NOT-NULL category
        final.append([row.get(h,'') for h in PHDR]); continue
    newcodes.append(t)
    r=raw.get(t, {'desc':t,'pack':'','uom':'','hs':'','cnr':''})
    src=pick_src(t)                        # carry curated attrs from a collapsing Jayson row
    row={h:'' for h in PHDR}
    row['code']=t
    row['description']=r['desc'] or (src.get('description','') if src else t)
    row[puc]=(src.get(puc,'').strip() if src else '') or mappack(r['pack'])
    row['default_uom']=(src.get('default_uom','').strip() if src else '') or r['uom'] or 'MT'
    if 'hs_code' in row: row['hs_code']=(src.get('hs_code','').strip() if src else '') or r['hs']
    if 'contract_number_reference' in row: row['contract_number_reference']=(src.get('contract_number_reference','').strip() if src else '') or r['cnr']
    if 'category' in row: row['category']=(src.get('category','').strip() if src else '') or pick_cat(t)
    row['is_active']='FALSE' if notinuse(r['desc']) else 'TRUE'
    if not row[puc]: unmapped_pack.append((t, r['pack'] or '(no src pack)'))
    final.append([row.get(h,'') for h in PHDR])
print(f"final Products rows={len(final)} (existing-kept={len(final)-len(newcodes)}, new-generic-added={len(newcodes)}: {newcodes})")
if unmapped_pack: print("UNMAPPED packing (left blank, review):", unmapped_pack)

# backup + overwrite Products
with open(f"{BK}/Products.pre-remaster.csv",'w',newline='') as f: csv.writer(f).writerows(jv)
retry(lambda: sheets.spreadsheets().values().clear(spreadsheetId=JAY,range="'Products'").execute())
retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range="'Products'!A1",valueInputOption='RAW',body={'values':[PHDR]+final}).execute())
print(f"Products rewritten: {len(jv)-1} -> {len(final)} rows (backup recon/backup/Products.pre-remaster.csv)")
cur=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
note=[['PASS 3 PRODUCTS RE-MASTER StepA 2026-07-01', f'Products {len(jv)-1}->{len(final)} generic master; dropped {len(dropped)}; new generic {len(newcodes)}. map->recon/out/product_map.json']]
retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
print("audited.")
