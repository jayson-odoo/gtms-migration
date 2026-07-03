# -*- coding: utf-8 -*-
"""PHASE 1 STEP D: remap the 3 product junctions missed earlier (surfaced by the prod dry-run).
- Contract Term x Product (contract_term, product): remap+dedupe
- Product Lot to UoM Conversion (code,...): remap+dedupe (code, UoM), refresh desc/cnr
- Inventory Location Packing Charges (packaging product): remap; reconstruct stripped 'HBAG'->PMQHBAG first
Uses recon/out/product_map.json. Backup + audit."""
import csv, json, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
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
def overwrite(t,header,rows):
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{t}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{t}'!A1",valueInputOption='RAW',body={'values':[header]+rows}).execute())
M=json.load(open('/home/src/recon/out/product_map.json')); mapping=M['mapping']
def mp(code):
    c=str(code).strip()
    if c in mapping: return mapping[c]
    if 'PMQ'+c in mapping: return mapping['PMQ'+c]   # reconstruct stripped bag code HBAG->PMQHBAG
    if 'TGQ'+c in mapping: return mapping['TGQ'+c]
    return None
pv=get('Products'); ph=[c.strip() for c in pv[0]]; pci=ph.index('code'); pdi=ph.index('description')
pcnr=ph.index('contract_number_reference') if 'contract_number_reference' in ph else None
gdesc={r[pci].strip():(r[pdi].strip() if len(r)>pdi else '') for r in pv[1:] if len(r)>pci and r[pci].strip()}
gcnr={r[pci].strip():(r[pcnr].strip() if pcnr is not None and len(r)>pcnr else '') for r in pv[1:] if len(r)>pci and r[pci].strip()}
log=[]
# 1) Contract Term x Product
t='Contract Term x Product'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]; ti=h.index('contract_term'); pi=h.index('product')
seen=set(); rows=[]
for r in v[1:]:
    if len(r)<=pi: continue
    g=mp(r[pi])
    if not g: continue
    k=(r[ti].strip(),g)
    if k in seen: continue
    seen.add(k); rows.append([r[ti].strip(),g])
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
# 2) Product Lot to UoM Conversion
t='Product Lot to UoM Conversion'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]
ci=h.index('code'); ui=h.index('UoM'); di=h.index('description') if 'description' in h else None; cnri=h.index('contract_number_reference') if 'contract_number_reference' in h else None
seen=set(); rows=[]
for r in v[1:]:
    r=r+['']*(len(h)-len(r)); g=mp(r[ci])
    if not g: continue
    k=(g,r[ui].strip())
    if k in seen: continue
    seen.add(k); nr=list(r); nr[ci]=g
    if di is not None: nr[di]=gdesc.get(g,nr[di])
    if cnri is not None: nr[cnri]=gcnr.get(g,nr[cnri])
    rows.append(nr[:len(h)])
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
# 3) Inventory Location Packing Charges (packaging product) - remap to full new code
t='Inventory Location Packing Charges'; v=get(t); backup(t,v); h=[c.strip() for c in v[0]]; ppi=h.index('packaging product')
gi=h.index('GTMS Inventory Location'); lb=h.index('lower_bound'); ub=h.index('upper_bound')
seen=set(); rows=[]; unres=[]
for r in v[1:]:
    r=r+['']*(len(h)-len(r)); orig=r[ppi].strip()
    if not orig: rows.append(r[:len(h)]); continue
    g=mp(orig)
    if not g: unres.append(orig); rows.append(r[:len(h)]); continue
    nr=list(r); nr[ppi]=g
    k=(nr[gi].strip(),g,nr[lb].strip(),nr[ub].strip())
    if k in seen: continue
    seen.add(k); rows.append(nr[:len(h)])
overwrite(t,h,rows); log.append((t,len(v)-1,len(rows)))
if unres: print("  packaging unresolved (left as-is):", sorted(set(unres)))
print("=== step D remap (tab: before -> after) ===")
for t,b,a in log: print(f"   {t:34} {b} -> {a}")
cur=get('RECON 300626 - Applied')
note=[['PASS 3 PRODUCTS RE-MASTER StepD (missed junctions) 2026-07-01', "; ".join(f"{t}:{b}->{a}" for t,b,a in log)]]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
print("backed up + audited.")
