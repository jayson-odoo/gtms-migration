# -*- coding: utf-8 -*-
"""Add raw-only Additonal Costs (from Additional Charges + Inventory Location Charges) with inferred
group, both profit centers, price. Backup + audit. Appends to Jayson 'Additonal Costs'."""
import io, re, csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; PUR='1SbnbbPgFkHHIy_5XnAm0ewVXX9Qw1vEa'; BK='/home/src/recon/backup'
PCS='QL FEED SDN. BHD.|QL INTERNATIONAL PTE. LTD.'
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
def isnum(s):
    try: float(s); return True
    except: return False
def banner(s): u=str(s).upper(); return 'SDN BHD' in u or 'PTE LTD' in u or 'QL FEED' in u or 'QL INTERNATIONAL' in u
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=PUR)); d=False
while not d: _,d=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True)
def rows(tab):
    ws=wb[tab]; return [[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]
# collect raw charges with price
raw={}  # nk -> (name, price, charges_type)
ac=rows('Additional Charges'); ach=[norm(x) for x in ac[0]]; nmi=ach.index('Name'); upi=ach.index('Unit Price'); cti=ach.index('Charges Type') if 'Charges Type' in ach else None
for r in ac[1:]:
    r=r+['']*(len(ach)-len(r)); idv=r[0].strip(); name=r[nmi].strip()
    if name and not re.fullmatch(r'[a-z]\.',idv) and isnum(idv):
        p=r[upi].strip() if isnum(r[upi]) else ''
        raw[nk(name)]=(name,p,(r[cti].strip() if cti is not None else ''))
il=rows('Inventory Location Charges'); ilh=[norm(x) for x in il[0]]; aci=ilh.index('Additional Cost'); upi2=ilh.index('Unit Price')
for r in il[1:]:
    r=r+['']*(len(ilh)-len(r)); name=r[aci].strip()
    if name and not banner(name):
        p=r[upi2].strip() if isnum(r[upi2]) else ''
        raw.setdefault(nk(name),(name,p,'Storage' if 'storage' in name.lower() else ''))
# jayson existing
jac=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'Additonal Costs'").execute()).get('values',[])
jh=[norm(x) for x in jac[0]]; jni=jh.index('name')
jset={nk(r[jni]) for r in jac[1:] if len(r)>jni and r[jni].strip()}
existing_groups={r[jh.index('additional cost group')].strip() for r in jac[1:] if len(r)>jh.index('additional cost group')}
# group inference
def infer_group(name):
    n=name.lower()
    if 'storage' in n or 'week' in n or 'month' in n: return 'Warehouse Charges'
    if 'warehouse' in n or 'handling' in n or 'unstuffing' in n or 'stuffing' in n or 'bagging' in n: return 'Warehouse Charges'
    if 'forwarding' in n or 'document' in n: return 'Forwarding Charges'
    if 'haulage' in n or 'lorry' in n or 'transport' in n: return 'Normal Haulage Charges'
    if 'port' in n or 'trimming' in n or 'tally' in n or 'hopper' in n or 'grab' in n or 'wharf' in n or 'kii' in n: return 'Port Charges'
    if 'agent' in n or 'agency' in n: return 'Shipping Agent Charges'
    return 'Other Charges'
# skip names that ARE existing group headers (not line-item charges)
GROUP_NAMES={nk(g) for g in existing_groups}|{nk(x) for x in ['Additional Charges','Handling Charges','Shipping Agent Charges','Port Charges','Forwarding & Documentation']}
new=[]
for k,(name,price,ct) in sorted(raw.items()):
    if k in jset: continue
    if k in GROUP_NAMES: continue   # skip group-header-like names
    grp=infer_group(name)
    dv=f"{float(price):.2f}" if isnum(price) else ''
    new.append(dict(name=name, description=name, **{'additional cost group':grp}, value_type='absolute',
                    default_value=dv, account_id='', transaction_type='', profit_centers=PCS,
                    contract_types='["1"]', charges_type=ct, is_active='TRUE'))
print(f"raw-only candidates={sum(1 for k in raw if k not in jset)} | after skipping group-headers -> to ADD={len(new)}")
for d in new: print(f"   + {d['name'][:46]:46} grp={d['additional cost group']:20} price={d['default_value'] or '-'}")
# append
hdr=[norm(x) for x in jac[0]]
with open(f"{BK}/Additonal Costs.pre-add.csv",'w',newline='') as f: csv.writer(f).writerows(jac)
rows_out=[[d.get(h,'') for h in hdr] for d in new]
retry(lambda: sheets.spreadsheets().values().append(spreadsheetId=JAY,range="'Additonal Costs'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows_out}).execute())
print(f"\nAdditonal Costs {len(jac)-1} -> {len(jac)-1+len(new)} (backup Additonal Costs.pre-add.csv)")
cur=retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range="'RECON 300626 - Applied'").execute()).get('values',[])
retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['PASS 4 Additonal Costs add (combined charges) 2026-07-01',f'{len(new)} added, both PCs, inferred groups']]}).execute())
print("audited.")
