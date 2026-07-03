# -*- coding: utf-8 -*-
"""Regenerate SpecGroupFIP under user rule: emit FIP rows ONLY for specs with a MIXED allowance tier
(both fip1 '1:1' and fip2 '2:1'); single-band specs get no FIP row. Map raw FIP block (product+origin,
all sellers) -> Jayson spec groups by product+origin. Writes staging tab 'RECON 300626 - SpecGroupFIP NEW'.
Compares to current Jayson SpecGroupFIP. Read-only (staging)."""
import io, re, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; PUR='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'
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
ORIG_WORDS=['ARGENTINA','BRAZILIAN','BRAZIL','INDIAN','INDIA','PAKISTAN','THAI','CHINESE','CHINA','USA','US','CANADIAN','CANADA','AUSTRALIAN','AUSTRALIA','UKRAINIAN','UKRAINE','MOLDOVA','PARAGUAYAN','PARAGUAY','LOCAL','MALAYSIA','CHILE']
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=PUR)); d=False
while not d: _,d=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True); ws=wb['SpecGroupFIP']
R=[[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]
h=[norm(x) for x in R[0]]
C0=h.index('SpecGroupName'); CO=h.index('SpecGroupName3 (Origin)'); CS=h.index('SpecGroupName4 (Seller)')
CSN=h.index('SpecName'); CVT=h.index('value_type'); CMN=h.index('minimum'); CMX=h.index('maximum')
# parse blocks with forward-filled SpecName; collect ratio tiers per (block,spec)
blocks=[]; cur=None; curspec=None
for row in R[1:]:
    row=row+['']*(len(h)-len(row))
    p=row[C0].strip()
    if p and not banner(p):
        cur={'product':p,'origins':[],'rows':[]}; blocks.append(cur); curspec=None
    if cur is None: continue
    o=row[CO].strip()
    if o and not banner(o) and not re.fullmatch(r'\((WM|EM)\)',o): cur['origins'].append(o)
    sn=row[CSN].strip()
    if sn: curspec=sn
    vt=row[CVT].strip(); mn=row[CMN].strip(); mx=row[CMX].strip()
    m=re.search(r'Allowances?\s*(\d+)\s*:\s*1', vt)
    if curspec and m and (mn or mx):
        cur['rows'].append((curspec, int(m.group(1)), mn, mx, vt))
# jayson spec groups for mapping
jsg=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroup'").execute()).get('values',[])
jn=[x.strip() for x in jsg[0]].index('name'); jgroups=[r[jn].strip() for r in jsg[1:] if len(r)>jn and r[jn].strip()]
def prodkey(s):  # strip origin words -> product core
    u=re.sub(r'\([^)]*\)',' ',str(s).upper())
    for w in ORIG_WORDS: u=re.sub(r'\b'+re.escape(w)+r'\b',' ',u)
    return nk(u)
jg_by_prod=defaultdict(list)
for g in jgroups: jg_by_prod[prodkey(g)].append(g)
def match_groups(product, origin):
    pk=prodkey(product); cand=jg_by_prod.get(pk,[])
    if origin:
        oi=nk(origin); sub=[g for g in cand if oi in nk(g)]
        if sub: return sub
    return cand
# build staging: only specs with BOTH fip1 and fip2
staging=[]; blk_summary=[]
for b in blocks:
    byspec=defaultdict(dict)  # spec -> {level:(min,max,vt)}
    for spec,lvl,mn,mx,vt in b['rows']:
        byspec[spec].setdefault(lvl,(mn,mx,vt))
    origin=b['origins'][0] if b['origins'] else ''
    grps=match_groups(b['product'], origin)
    for spec,lvls in byspec.items():
        if 1 in lvls and 2 in lvls:   # MIXED -> emit fip1 + fip2
            for lvl in (1,2):
                mn,mx,vt=lvls[lvl]
                for g in (grps or [f"(UNMATCHED) {b['product']} {origin}"]):
                    staging.append([g, spec, mn, mx, str(lvl), b['product'], origin, vt[:60]])
    mixed=[s for s,l in byspec.items() if 1 in l and 2 in l]
    if mixed: blk_summary.append((b['product'], origin, mixed, len(grps)))
print(f"raw FIP blocks={len(blocks)} | blocks with a MIXED(1&2) spec={len(blk_summary)}")
print("mixed-tier specs by block (product | origin | specs | #jayson groups matched):")
for p,o,ms,ng in blk_summary: print(f"   {p[:28]:28} {o[:14]:14} {ms} -> {ng} groups")
# current jayson FIP
jfip=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'SpecGroupFIP'").execute()).get('values',[])
jfh=[x.strip() for x in jfip[0]]
jset=set()
for r in jfip[1:]:
    r=r+['']*(len(jfh)-len(r)); jset.add((nk(r[0]),nk(r[1]),r[jfh.index('fip')].strip()))
newset={(nk(s[0]),nk(s[1]),s[4]) for s in staging}
print(f"\nregenerated FIP rows (mixed only)={len(staging)} | current jayson FIP={len(jfip)-1}")
print(f"   in regen NOT in jayson (missing) = {len(newset-jset)}")
print(f"   in jayson NOT in regen (extra/diff) = {len(jset-newset)}")
# distinct specs that qualify as FIP
print("   distinct mixed FIP specs:", sorted(set(s[1] for s in staging)))
# write staging
title='RECON 300626 - SpecGroupFIP NEW'
meta=retry(lambda: sheets.spreadsheets().get(spreadsheetId=JAY).execute())
if title not in [s['properties']['title'] for s in meta['sheets']]:
    retry(lambda: sheets.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
retry(lambda: sheets.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
hdr=['SpecGroupName','SpecName','minimum','maximum','fip','raw_product','raw_origin','raw_value_type']
note=[[f'STAGING (review): regenerated SpecGroupFIP under rule "only specs with MIXED fip 1 & 2". {len(staging)} rows across {len(blk_summary)} mixed blocks. Review then tell me to go live.']]
retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':note+[[]]+[hdr]+staging}).execute())
print(f"\nwrote staging '{title}' ({len(staging)} rows)")
