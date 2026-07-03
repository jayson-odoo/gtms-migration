# -*- coding: utf-8 -*-
"""User decision: TRIM Payment Term to EQUAL the 30 source terms (Account file 'Payment Term' tab).
Rebuild 'Payment Term' = 30 source rows; regenerate dependents 'Payment Term Configs' (30x6=180) and
'Payment Term x Profit Center' (30x2=60) so name-FK resolution stays intact. Backup all 3 + audit.
DB re-migration (le_load_master_payment_terms + lnk configs/counterparties + FK-ordered stale delete)
is PENDING the SSM tunnel."""
import glob, csv, time
import openpyxl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
D='/home/src/raw_master/300626'; BK='/home/src/recon/backup'
DOCS=['advance_payment_voucher','payment_voucher','provisional_invoice','invoice','advance_invoice','credit_note']
PCS=['QL FEED SDN. BHD.','QL INTERNATIONAL PTE. LTD.']
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def backup(t):
    v=get(t)
    with open(f"{BK}/{t}.pre-pttrim.csv",'w',newline='') as f: csv.writer(f).writerows(v)
    return v
def rewrite(t, rows):
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{t}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{t}'!A1",valueInputOption='RAW',body={'values':rows}).execute())

# ---- read 30 raw source rows ----
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Packing Unit, Trader, Payment Term' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['Payment Term']
raw=[[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows(max_row=60)]
raw=[r for r in raw if any(x for x in r)]; rh=raw[0]
def rc(r,name):
    i=rh.index(name); return r[i] if i<len(r) else ''
src=[]
for r in raw[1:]:
    src.append({'id':rc(r,'M3 Code'),'name':rc(r,'M3 Description'),'contract_description':rc(r,'contract_description'),
                'invoice_description':rc(r,'invoice_description'),'due_date_days':rc(r,'due_date_days'),
                'payment_mode':rc(r,'payment_mode'),'lc_type':rc(r,'lc_type')})
names=[s['name'] for s in src]
assert len(names)==len(set(names))==30, f"expected 30 distinct names, got {len(names)}/{len(set(names))}"

# ---- 1) Payment Term ----
pt=backup('Payment Term'); pth=[c.strip() for c in pt[0]]
pt_rows=[pth]+[[s.get(c,'') for c in pth] for s in src]
rewrite('Payment Term', pt_rows)
print(f"Payment Term: {len(pt)-1} -> {len(src)} rows (backup .pre-pttrim.csv)")

# ---- 2) Payment Term Configs (30 x 6) ----
cfg=backup('Payment Term Configs'); cfgh=[c.strip() for c in cfg[0]]
cfg_rows=[cfgh]; i=1
for nm in names:
    for doc in DOCS:
        d={'id':i,'payment_term':nm,'document_type':doc,'percentage':'100','billed_basis':'loaded_weight'}
        cfg_rows.append([d.get(c,'') for c in cfgh]); i+=1
rewrite('Payment Term Configs', cfg_rows)
print(f"Payment Term Configs: {len(cfg)-1} -> {len(cfg_rows)-1} rows ({len(names)}x{len(DOCS)})")

# ---- 3) Payment Term x Profit Center (30 x 2) ----
px=backup('Payment Term x Profit Center'); pxh=[c.strip() for c in px[0]]
px_rows=[pxh]
for nm in names:
    for pc in PCS:
        d={'name':nm,'counterparty':pc,'is_internal':'TRUE','transaction_type':''}
        px_rows.append([d.get(c,'') for c in pxh])
rewrite('Payment Term x Profit Center', px_rows)
print(f"Payment Term x Profit Center: {len(px)-1} -> {len(px_rows)-1} rows ({len(names)}x{len(PCS)})")

cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',
      body={'values':cur+[[]]+[['PAYMENT TERM TRIM-TO-SOURCE 2026-07-02',f'Payment Term 50->30 (=source); Configs 300->180; PT x Profit Center 100->60. DB re-migration pending tunnel.']]}).execute())
print("audited. NOTE: DB migration pending tunnel (re-run le/lnk payment-term pipelines + FK-ordered stale-name delete).")
