# -*- coding: utf-8 -*-
"""PHASE 1 STEP B+C: remap product junctions to the generic master (uses recon/out/product_map.json).
B (regenerate full coverage): Profit Center x Product (39x2), Product x Contract Type (39x1).
C (remap+dedupe associations): Spec Group x Product, Price Index Product, Product UoM Conversion,
SpecGroup 'Product M3 Code'. Each tab backed up. Audit."""
import csv, json, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
PCS=['QL FEED SDN. BHD.','QL INTERNATIONAL PTE. LTD.']
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def backup(t,v):
    with open(f"{BK}/{t}.pre-remap.csv",'w',newline='') as f: csv.writer(f).writerows(v)
def overwrite(t, header, rows):
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{t}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{t}'!A1",valueInputOption='RAW',body={'values':[header]+rows}).execute())
m=json.load(open('/home/src/recon/out/product_map.json'))
mapping=m['mapping']; targets=sorted(set(m['targets']))
def mp(code):  # map a product code -> generic, or None if dropped/unknown
    c=str(code).strip(); return mapping.get(c)   # DROP codes are absent from mapping

# generic product desc/cnr for refreshing UoM conversion rows
pv=get('Products'); ph=[c.strip() for c in pv[0]]; pci=ph.index('code'); pdi=ph.index('description')
pcnr=ph.index('contract_number_reference') if 'contract_number_reference' in ph else None
gdesc={r[pci].strip():(r[pdi].strip() if len(r)>pdi else '') for r in pv[1:] if len(r)>pci and r[pci].strip()}
gcnr={r[pci].strip():(r[pcnr].strip() if pcnr is not None and len(r)>pcnr else '') for r in pv[1:] if len(r)>pci and r[pci].strip()}

log=[]
# ---- B1: Profit Center x Product = 39 x 2 ----
t='Profit Center x Product'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]
rows=[[pc,prod] for pc in PCS for prod in targets]
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
# ---- B2: Product x Contract Type = 39 x '1' ----
t='Product x Contract Type'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]
rows=[[prod,'1'] for prod in targets]
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
# ---- C1: Spec Group x Product (spec_group, code) remap+dedupe ----
t='Spec Group x Product'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]; ci=h.index('code'); si=h.index('spec_group')
seen=set(); rows=[]
for r in v[1:]:
    if len(r)<=ci: continue
    g=mp(r[ci])
    if not g: continue
    key=(r[si].strip(),g)
    if key in seen: continue
    seen.add(key); rows.append([r[si].strip(),g])
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
# ---- C2: Price Index Product (code, product) remap+dedupe ----
t='Price Index Product'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]; ci=h.index('code'); pi=h.index('product')
seen=set(); rows=[]
for r in v[1:]:
    if len(r)<=pi: continue
    g=mp(r[pi])
    if not g: continue
    key=(r[ci].strip(),g)
    if key in seen: continue
    seen.add(key); rows.append([r[ci].strip(),g])
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
# ---- C3: Product UoM Conversion (code,cnr,desc,From,To,mult) remap+dedupe, refresh desc/cnr ----
t='Product UoM Conversion'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]
ci=h.index('code'); fi=h.index('From UoM'); ti=h.index('To UoM')
di=h.index('description') if 'description' in h else None; cnri=h.index('contract_number_reference') if 'contract_number_reference' in h else None
seen=set(); rows=[]
for r in v[1:]:
    r=r+['']*(len(h)-len(r))
    g=mp(r[ci])
    if not g: continue
    key=(g,r[fi].strip(),r[ti].strip())
    if key in seen: continue
    seen.add(key); nr=list(r)
    nr[ci]=g
    if di is not None: nr[di]=gdesc.get(g,nr[di])
    if cnri is not None: nr[cnri]=gcnr.get(g,nr[cnri])
    rows.append(nr[:len(h)])
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
# ---- C4: SpecGroup 'Product M3 Code' remap in place ----
t='SpecGroup'; v=get(t); h=[c.strip() for c in v[0]]
if 'Product M3 Code' in h:
    backup(t,v); pmi=h.index('Product M3 Code'); changed=0
    rows=[]
    for r in v[1:]:
        r=r+['']*(len(h)-len(r)); cur=r[pmi].strip()
        if cur:
            g=mp(cur)
            if g and g!=cur: r[pmi]=g; changed+=1
            elif not g: r[pmi]=''  # dropped product -> clear
        rows.append(r[:len(h)])
    overwrite(t,h,rows); log.append((t+' (Product M3 Code)',f'{changed} remapped',len(rows)))

print("=== junction remap summary (tab: before -> after) ===")
for t,b,a in log: print(f"   {t:34} {b} -> {a}")
cur=get('RECON 300626 - Applied')
note=[['PASS 3 PRODUCTS RE-MASTER StepB+C 2026-07-01', "; ".join(f"{t}:{b}->{a}" for t,b,a in log)]]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
print("backed up (*.pre-remap.csv) + audited.")
