# -*- coding: utf-8 -*-
"""Analyze raw SpecGroup / SpecGroupFIP block structure vs Jayson SpecGroup / Spec Group Spec / SpecGroupFIP.
Also Counterparty v2 vs raw Vendor+Customer by M3 code."""
import io, re, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
PUR='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'
creds=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/spreadsheets'])
drive=build('drive','v3',credentials=creds,cache_discovery=False); sheets=build('sheets','v4',credentials=creds,cache_discovery=False)
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def load(fid):
    buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=fid)); d=False
    while not d: _,d=dl.next_chunk()
    buf.seek(0); return openpyxl.load_workbook(buf, data_only=True, read_only=True)
def rows_of(wb,tab): 
    ws=wb[tab]; return [[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]
def getj(t): return sheets.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute().get('values',[])
def banner(s): u=str(s).upper(); return 'SDN BHD' in u or 'PTE LTD' in u or 'QL FEED' in u or 'QL INTERNATIONAL' in u
pur=load(PUR)

def parse_blocks(tab, pcol):
    r=rows_of(pur,tab); h=[re.sub(r'\s+',' ',x).strip() for x in r[0]]
    P=h.index(pcol); O=h.index('SpecGroupName3 (Origin)'); S=h.index('SpecGroupName4 (Seller)'); SN=h.index('SpecName')
    mn=h.index('minimum'); mx=h.index('maximum')
    blocks=[]; cur=None
    for row in r[1:]:
        row=row+['']*(len(h)-len(row))
        p=row[P].strip()
        if p and not banner(p):
            cur={'product':p,'origins':set(),'sellers':set(),'specs':[]}; blocks.append(cur)
        if cur is None: continue
        o=row[O].strip(); s=row[S].strip(); sn=row[SN].strip()
        if o and not banner(o): cur['origins'].add(o)
        if s and not banner(s): cur['sellers'].add(s)
        if sn and (row[mn].strip() or row[mx].strip()): cur['specs'].append(sn)
    return blocks

sg=parse_blocks('SpecGroup','SpecGroupName2')
fip=parse_blocks('SpecGroupFIP','SpecGroupName')
def summ(blocks,label):
    prods=set(nk(b['product']) for b in blocks)
    nspecs=sum(len(b['specs']) for b in blocks)
    print(f"### RAW {label}: blocks={len(blocks)} distinct_products={len(prods)} total_spec_lines={nspecs}")
    for b in blocks[:6]:
        print(f"     {b['product'][:22]:22} origins={len(b['origins'])} sellers={len(b['sellers'])} specs={b['specs']}")
    return prods
sgp=summ(sg,'SpecGroup'); fipp=summ(fip,'SpecGroupFIP')

jsg=getj('SpecGroup'); jsgh=[x.strip() for x in jsg[0]]; jni=jsgh.index('name')
jsg_names=[r[jni].strip() for r in jsg[1:] if len(r)>jni and r[jni].strip()]
jspec=getj('Spec Group Spec'); jfip=getj('SpecGroupFIP')
print(f"\n### JAYSON: SpecGroup={len(jsg_names)} | Spec Group Spec={len(jspec)-1} | SpecGroupFIP={len(jfip)-1}")
# which raw products have NO jayson spec group mentioning them
jsg_blob=nk(' '.join(jsg_names))
missing=[b['product'] for b in sg if nk(b['product']) not in jsg_blob]
print("### RAW SpecGroup products NOT found in any Jayson SpecGroup name:")
seen=set()
for m in missing:
    if nk(m) not in seen: seen.add(nk(m)); print("     -",m)
# FIP: raw fip products vs jayson fip
jfh=[x.strip() for x in jfip[0]]; jfn=jfh.index('SpecGroupName') if 'SpecGroupName' in jfh else 0
jfip_names=set(nk(r[jfn]) for r in jfip[1:] if len(r)>jfn and r[jfn].strip())
print(f"\n### FIP DETAIL: raw FIP has {sum(len(b['specs']) for b in fip)} spec lines across {len(fip)} blocks; jayson FIP={len(jfip)-1} rows")
print("   raw FIP distinct spec names:", sorted(set(s for b in fip for s in b['specs']))[:15])

# ---------- COUNTERPARTY v2 vs raw Vendor+Customer (M3 code) ----------
def codes(tab):
    r=rows_of(pur,tab); 
    # header row may be 0 or 1; find row with 'M3' code col
    hi=0
    for i,row in enumerate(r[:3]):
        if any('M3' in str(c).upper() and 'CODE' in str(c).upper() for c in row): hi=i; break
    h=[re.sub(r'\s+',' ',x).strip() for x in r[hi]]
    ci=next((i for i,x in enumerate(h) if 'M3' in x.upper() and 'CODE' in x.upper()),None)
    if ci is None: return set()
    return {nk(x[ci]) for x in r[hi+1:] if len(x)>ci and x[ci].strip()}
rawcp=codes('Vendor')|codes('Customer')
jcp=getj('Counterparty v2'); jch=[x.strip() for x in jcp[0]]
mci=jch.index('M3 Code'); mvi=jch.index('M3 Vendor Code (for merged vendor & customer)')
jcpcodes=set()
for r in jcp[1:]:
    r=r+['']*(len(jch)-len(r))
    if r[mci].strip(): jcpcodes.add(nk(r[mci]))
    if r[mvi].strip(): jcpcodes.add(nk(r[mvi]))
print(f"\n### COUNTERPARTY: raw Vendor+Customer(Purchasing) M3 codes={len(rawcp)} | Jayson Cpv2 codes(incl merged)={len(jcpcodes)}")
print(f"   raw codes NOT in Jayson Cpv2 = {len(rawcp-jcpcodes)}: {sorted(rawcp-jcpcodes)[:30]}")
