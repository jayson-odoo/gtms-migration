# -*- coding: utf-8 -*-
"""Corrected raw-vs-jayson validation for the entities the user flagged. Part 1: Additonal Costs
(raw Additional Charges UNION Inventory Location Charges), Payment Term (PT_A union PT_B by M3 Code)."""
import io, re, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
PUR='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'; PTA='1H2h-wCSjCvRzcaefBye1zNHtBOOA5m2U'; PTB='1RNaMj4IbIiyAlGOOfBKtt39WCSy4pp27'
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
def load(fid):
    buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=fid)); d=False
    while not d: _,d=dl.next_chunk()
    buf.seek(0); return openpyxl.load_workbook(buf, data_only=True, read_only=True)
def rows_of(wb, tab):
    ws=wb[tab]; return [[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]
def getj(t): return retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def isnum(s):
    try: float(s); return True
    except: return False

pur=load(PUR)
# ---------- ADDITONAL COSTS: raw Additional Charges (Name, line items) UNION Inv Loc Charges (Additional Cost) ----------
ac=rows_of(pur,'Additional Charges'); ach=[norm(x) for x in ac[0]]; nmi=ach.index('Name')
raw_ac=set(); raw_ac_disp={}
for r in ac[1:]:
    r=r+['']*(len(ach)-len(r))
    idv=r[0].strip(); name=r[nmi].strip()
    if not name: continue
    if re.fullmatch(r'[a-z]\.', idv): continue        # a./b. group headers
    if not isnum(idv): continue                        # only numbered line items
    raw_ac.add(nk(name)); raw_ac_disp[nk(name)]=name
il=rows_of(pur,'Inventory Location Charges'); ilh=[norm(x) for x in il[0]]; aci=ilh.index('Additional Cost')
for r in il[1:]:
    r=r+['']*(len(ilh)-len(r)); name=r[aci].strip()
    if name: raw_ac.add(nk(name)); raw_ac_disp.setdefault(nk(name),name)
jac=getj('Additonal Costs'); jh=[norm(x) for x in jac[0]]; jni=jh.index('name')
jset={nk(r[jni]) for r in jac[1:] if len(r)>jni and r[jni].strip()}
jdisp={nk(r[jni]):r[jni].strip() for r in jac[1:] if len(r)>jni and r[jni].strip()}
onlyraw=sorted(raw_ac-jset); onlyjay=sorted(jset-raw_ac)
print(f"### ADDITONAL COSTS: raw(AddCharges + InvLocCharges)={len(raw_ac)} distinct | jayson={len(jset)}")
print(f"   only in RAW (not in Additonal Costs) = {len(onlyraw)}:")
for k in onlyraw: print("      +", raw_ac_disp[k])
print(f"   only in JAYSON (not in raw) = {len(onlyjay)}  (first 25):")
for k in onlyjay[:25]: print("      -", jdisp[k])

# ---------- PAYMENT TERM: PT_A union PT_B by M3 Code, vs Jayson (join invoice_description) ----------
def pt_codes(fid):
    wb=load(fid); r=rows_of(wb,'Payment Term'); h=[norm(x) for x in r[0]]; ci=h.index('M3 Code')
    return {nk(x[ci]):x[ci].strip() for x in r[1:] if len(x)>ci and x[ci].strip()}
rawpt={}; rawpt.update(pt_codes(PTA)); rawpt.update(pt_codes(PTB))
jpt=getj('Payment Term'); jph=[norm(x) for x in jpt[0]]
jinv=jph.index('invoice_description') if 'invoice_description' in jph else None
jname=jph.index('name')
jpt_keys=set(); 
for r in jpt[1:]:
    r=r+['']*(len(jph)-len(r))
    k=nk(r[jinv]) if jinv is not None and r[jinv].strip() else nk(r[jname])
    if k: jpt_keys.add(k)
pr=set(rawpt); onlyraw_pt=sorted(pr-jpt_keys); onlyjay_pt=sorted(jpt_keys-pr)
print(f"\n### PAYMENT TERM: raw(PT_A+PT_B by M3 Code)={len(pr)} | jayson(by invoice_desc/name)={len(jpt_keys)}")
print(f"   only in RAW = {len(onlyraw_pt)}: {[rawpt[k] for k in onlyraw_pt]}")
print(f"   only in JAYSON = {len(onlyjay_pt)}: {onlyjay_pt[:40]}")
