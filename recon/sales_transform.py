# -*- coding: utf-8 -*-
"""Transform GTMS_SC_230626 sales-contract source into Jayson.
A: Product Spec_SC -> SpecGroup.sales_spec_group_description (OVERWRITE matched groups by product+origin).
B: QLF/QLI contract clauses -> Document Content Snippet (one per category+variant, template id 5).
Backup + audit."""
import io, re, csv, time
from collections import defaultdict, OrderedDict
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
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def getj(t): return retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=FID)); d=False
while not d: _,d=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True)
def rowsof(t): ws=wb[t]; return [[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]

# ===== PART A: Product Spec_SC -> sales_spec_group_description =====
ps=rowsof('Product Spec_SC'); blocks=[]; cur=None
for r in ps:
    r=r+['']*(3-len(r))
    if r[0].strip(): cur={'product':r[0].strip(),'lines':[]}; blocks.append(cur)
    elif cur is not None and (r[1].strip() or r[2].strip()):
        cur['lines'].append((r[1].strip()+'\t'+r[2].strip()).strip())
ORIG={'ARGENTINA':'ARGENTINA','BRAZILLIAN':'BRAZIL','BRAZILIAN':'BRAZIL','BRAZIL':'BRAZIL','U.S.':'US','U. S.':'US','US ':'US','UNITED STATES':'US','CHINA':'CHINA','AUSTRALIAN':'AUSTRALIA','AUSTRALIA':'AUSTRALIA','LOCAL':'LOCAL','CHILE':'CHILE','PARAGUAY':'PARAGUAY'}
def origin_of(s):
    u=' '+s.upper()+' '
    for k,v in ORIG.items():
        if k in u: return v
    return ''
def prodcore(s):
    u=s.upper()
    for k in list(ORIG)+['H-PRO','HI-PRO','H PRO','HI PRO','YELLOW','STEAM DRIED','EXPORT','(HSC-LH)','TVBN','150','120','65%','60%','55%']:
        u=u.replace(k,' ')
    u=u.replace('SOYABEAN','SOYA BEAN')
    return nk(u)
sg=getj('SpecGroup'); sh=[x.strip() for x in sg[0]]; ni=sh.index('name'); sdi=sh.index('sales_spec_group_description')
# group core+origin index
def g_origin(name):
    u=' '+name.upper()+' '
    for k,v in ORIG.items():
        if k in u or ('UNITED STATES' in u): 
            if k in u: return v
    if 'UNITED STATES' in u or ' US ' in u: return 'US'
    return ''
matches=defaultdict(list)  # (core,origin) -> raw block
for b in blocks:
    matches[(prodcore(b['product']), origin_of(b['product']))].append(b)
updates=[]; applied=[]; unmatched=set(b['product'] for b in blocks)
for ri,r in enumerate(sg[1:],start=2):
    nm=r[ni].strip() if len(r)>ni else ''
    if not nm: continue
    gc=prodcore(nm); go=g_origin(nm)
    key=(gc,go); alt=(gc,'')
    hit=matches.get(key) or matches.get(alt)
    if hit:
        b=hit[0]; text='\n'.join(b['lines'])
        col=chr(65+sdi) if sdi<26 else 'A'+chr(65+sdi-26)
        updates.append({'range':f"'SpecGroup'!{col}{ri}",'values':[[text]]}); applied.append((nm,b['product']))
        unmatched.discard(b['product'])
print(f"### PART A: raw products={len(blocks)} | spec groups overwritten={len(applied)} | raw products unmatched={sorted(unmatched)}")
# backup SpecGroup, apply
with open(f"{BK}/SpecGroup.pre-salesdesc.csv",'w',newline='') as f: csv.writer(f).writerows(sg)
if updates: retry(lambda: sheets.spreadsheets().values().batchUpdate(spreadsheetId=JAY,body={'valueInputOption':'RAW','data':updates}).execute())
print(f"   overwrote {len(updates)} sales_spec_group_description cells")

# ===== PART B: QLF/QLI clauses -> Document Content Snippet =====
def parse_qlf(tab, market):
    r=rowsof(tab); out=OrderedDict(); cat=''; variant=''
    for row in r:
        row=row+['']*(3-len(row))
        c0,c1,c2=row[0].strip(),row[1].strip(),row[2].strip()
        if c0 and len(c0)<40 and not c0[0].isdigit(): cat=c0; variant=''   # new category (short label)
        if c1 in ('FM','Comm','WT','QLV','FARM'): variant=c1
        txt=c2 or (c0 if (c0 and c0[0].isdigit()) else '')
        if not txt and c0 and len(c0)>=40: txt=c0   # continuation long line in col0
        if cat and txt:
            k=(cat,variant); out.setdefault(k,[]).append(txt)
    return [(cat,variant,'\n'.join(v)) for (cat,variant),v in out.items()]
def parse_qli(tab):
    r=rowsof(tab); out=OrderedDict(); cat=''
    for row in r:
        row=row+['']*(4-len(row))
        c0,c3=row[0].strip(),row[3].strip()
        if c0 and len(c0)<40: cat=c0
        txt=c3
        if cat and txt: out.setdefault(cat,[]).append(txt)
    return [(cat,'','\n'.join(v)) for cat,v in out.items()]
qlf=parse_qlf('QLF_contract clauses','QLF'); qli=parse_qli('QLI_contract clauses')
dcs=getj('Document Content Snippet'); dch=[x.strip() for x in dcs[0]]
existing={nk(r[0]) for r in dcs[1:] if r and r[0].strip()}
snips=[]
for mkt,rows in [('QLF',qlf),('QLI',qli)]:
    for cat,variant,text in rows:
        nm=f"Sales Contract - {cat} ({mkt}{'/'+variant if variant else ''})"
        if nk(nm) in existing: continue
        snips.append({'name':nm,'printout_description':text,'document_template_id':'5','is_active':'TRUE'})
print(f"\n### PART B: QLF clauses={len(qlf)} QLI clauses={len(qli)} -> new snippets={len(snips)}")
for s in snips[:8]: print("   +", s['name'])
with open(f"{BK}/Document Content Snippet.pre-add.csv",'w',newline='') as f: csv.writer(f).writerows(dcs)
rows_out=[[s.get(h,'') for h in dch] for s in snips]
if rows_out: retry(lambda: sheets.spreadsheets().values().append(spreadsheetId=JAY,range="'Document Content Snippet'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows_out}).execute())
print(f"   Document Content Snippet {len(dcs)-1} -> {len(dcs)-1+len(snips)}")
cur=getj('RECON 300626 - Applied')
retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 6 Sales Contract transform 2026-07-01',f'{len(applied)} sales-desc overwritten, {len(snips)} snippets added']]}).execute())
print("audited.")
