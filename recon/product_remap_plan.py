# -*- coding: utf-8 -*-
"""READ-ONLY: build clean generic raw master, propose Jayson->generic mapping, inventory junctions.
Writes review tab 'RECON 300626 - Product Remap'. No deletes."""
import re, io, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'
RAW_ID='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
TEST={'CORN','SB','SBM','SBO','DDGS','DUMMY'}
ORIGIN_WORDS=['ARGENTINA','ARGENTINE','BRAZILIAN','BRAZIL','BRZ','INDIAN','INDIA','PAKISTAN','PAKISTANI','THAI','CHINESE','CHINA','USA','US','CANADIAN','CANADA','AUSTRALIAN','AUSTRALIA','UKRAINIAN','UKRAINE','MOLDOVA','PARAGUAYAN','PARAGUAY','LOCAL','MALAYSIA','MAL','CHILE','GEN.PURPOSE','GENERAL PURPOSE']
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
    u=re.sub(r'\([^)]*\)',' ',str(desc).upper())     # drop parentheticals
    for w in ORIGIN_WORDS: u=re.sub(r'\b'+re.escape(w)+r'\b',' ',u)
    u=u.replace('NO.2','').replace('NO. 2','').replace('OR BETTER','').replace('YELLOW','')
    return re.sub(r'[^A-Z0-9]','',u)
creds=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/spreadsheets'])
drive=build('drive','v3',credentials=creds,cache_discovery=False); sheets=build('sheets','v4',credentials=creds,cache_discovery=False)
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=RAW_ID))
done=False
while not done: _,done=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True); ws=wb['Products']
rows=list(ws.iter_rows(min_row=1)); hdr=[str(c.value).strip() if c.value is not None else '' for c in rows[0]]
mi=hdr.index('M3 Code'); di=hdr.index('description'); oidx=[i for i,h in enumerate(hdr) if h.startswith('origin')]
# clean generic master: dedupe by code, drop banner/test, prefer non-NOT-IN-USE
raw={}
for r in rows[1:]:
    code=r[mi].value if len(r)>mi else None
    if not code or not str(code).strip(): continue
    c=str(code).strip()
    if c in TEST or banner(c): continue
    desc=str(r[di].value).strip() if len(r)>di and r[di].value else ''
    origins=[str(r[i].value).strip() for i in oidx if len(r)>i and r[i].value and str(r[i].value).strip()]
    if c not in raw or (notinuse(raw[c][0]) and not notinuse(desc)):
        raw[c]=(desc,origins)
print(f"### CLEAN generic raw master = {len(raw)} products")
raw_by_base=defaultdict(list)
for c,(d,o) in raw.items(): raw_by_base[base(d)].append(c)

# Jayson products
jv=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'Products'").execute()).get('values',[])
jh=[c.strip() for c in jv[0]]; jci=jh.index('code'); jdi=jh.index('description')
jrows=[(r[jci].strip(),(r[jdi].strip() if len(r)>jdi else '')) for r in jv[1:] if len(r)>jci and r[jci].strip()]

# explicit overrides for family cases the base-matcher misses, + junk drops (domain-reviewed)
OVR={
 'TGQHDDG':'TGQDDG','TGQHDDGL':'TGQDDGL',
 'TGQHWGAU':'TGQWG','TGQHWGM':'TGQWG','TGQHWGP':'TGQWG','TGQHWGU':'TGQWG','TGQHWGUS':'TGQWG',
 'TGQHSBAH':'TGQSBM','TGQHSBPHP':'TGQSBM','TGQHSBBH':'TGQSBM','TGQHSBUSHP':'TGQSBM',
 'TGQHSBLH':'TGQSBMHPL','TGQHSBUS':'TGQSB',
}
DROP={'PMQHBAG','TGQHDDGH','TGQHLME','TGQHMDCP','TGQHOTMT'}  # NOT-IN-USE / junk
FLAG={'TGQHDMX7'}  # DMX-7 vs raw DMX PLUS: distinct variant, user decides keep/drop
mapping=[]  # jcode, jdesc, target_raw_code, target_raw_desc, type
for jc,jd in jrows:
    if jc in DROP: mapping.append((jc,jd,'','','DROP (not-in-use/junk)')); continue
    if jc in FLAG: mapping.append((jc,jd,'','','REVIEW (no raw equiv - keep/drop?)')); continue
    if jc in OVR: t=OVR[jc]; mapping.append((jc,jd,t,raw.get(t,('?',))[0],'MAP (override)')); continue
    if jc in raw:  # already a generic raw code (e.g. my added ones)
        mapping.append((jc,jd,jc,raw[jc][0],'KEEP (is raw code)')); continue
    b=base(jd); cands=raw_by_base.get(b,[])
    if len(cands)==1: mapping.append((jc,jd,cands[0],raw[cands[0]][0],'MAP'))
    elif len(cands)>1: mapping.append((jc,jd,'|'.join(cands),' / '.join(raw[x][0] for x in cands),'AMBIGUOUS - pick one'))
    else: mapping.append((jc,jd,'','','NO MATCH -> drop or new?'))

from collections import Counter
print("map types:", Counter(m[4] for m in mapping))
# collapse view: how many jayson -> each target
coll=defaultdict(list)
for jc,jd,tc,td,t in mapping:
    if t in ('MAP','KEEP (is raw code)') and tc: coll[tc].append(jc)
print("\n### COLLAPSES (target raw <- multiple jayson):")
for tc,js in sorted(coll.items(), key=lambda x:-len(x[1])):
    if len(js)>1: print(f"   {tc} ({raw[tc][0][:34]}) <- {len(js)}: {js}")
print("\n### NO-MATCH jayson products (would be dropped):")
for jc,jd,tc,td,t in mapping:
    if t.startswith('NO MATCH'): print(f"   {jc:13} {jd[:44]}")
print("\n### AMBIGUOUS (need manual pick):")
for jc,jd,tc,td,t in mapping:
    if t=='AMBIGUOUS': print(f"   {jc:13} {jd[:36]} -> {tc}")

# junction inventory: tabs with a product-code column
print("\n### JUNCTION tabs referencing products (tab | rows | product-col):")
CAND_TABS=['Profit Center x Product','Product x Contract Type','Spec Group x Product','Price Index Product','Product UoM Conversion','SpecGroup','Product x Product','Integration Reference']
for t in CAND_TABS:
    try:
        v=retry(lambda t=t: sheets.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
    except Exception as e:
        print(f"   {t}: (missing)"); continue
    if not v: print(f"   {t}: empty"); continue
    h=[c.strip() for c in v[0]]
    pcol=next((c for c in h if c.lower() in ('product','product m3 code','product code','m3 code','code','productcode') or 'product' in c.lower() and 'code' in c.lower()),None)
    print(f"   {t}: rows={len(v)-1} cols={h[:6]} product_col={pcol!r}")

# write review tab
title='RECON 300626 - Product Remap'
meta=retry(lambda: sheets.spreadsheets().get(spreadsheetId=JAY).execute())
if title not in [s['properties']['title'] for s in meta['sheets']]:
    retry(lambda: sheets.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
retry(lambda: sheets.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
note=['READ-ONLY proposed mapping: old Jayson product -> generic raw product (origin moves to spec groups). Review/fix target_code + action, then I execute the re-master. NO-MATCH rows will be dropped unless you set a target.']
hdr2=['jayson_code','jayson_desc','target_raw_code','target_raw_desc','action']
body=[note,[],hdr2]+[list(m) for m in mapping]
retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':body}).execute())
print(f"\nwrote review tab '{title}' ({len(mapping)} rows)")
