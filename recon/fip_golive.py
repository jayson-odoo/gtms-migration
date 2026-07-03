# -*- coding: utf-8 -*-
"""Generate SpecGroupFIP protein-band rows for the 12 new soya groups lacking FIP.
Two fixed templates keyed on protein grade (reverse-engineered from existing 24 FIP rows):
  46% grade (band 45.5-46.5): fip1 46-46.5, fip2 45.5-46
  47% grade (band 47-48):     fip1 47.5-48, fip2 47-47.5
Grade detected from each group's Protein spec band. LOCAL-MALAYSIA (36%) excluded (no template).
Add-only. Backup + audit."""
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range=f"'{t}'").execute()).get('values',[])
def N(s): return " ".join(str(s).split()).strip().upper()
def flt(s):
    try: return float(str(s).strip())
    except: return None
TPL={'46':[('46','46.5','1'),('45.5','46','2')], '47':[('47.5','48','1'),('47','47.5','2')]}

fip=get('SpecGroupFIP'); fh=[h.strip() for h in fip[0]]
fip_groups={N(dict(zip(fh,r)).get('SpecGroupName','')) for r in fip[1:]}
sgs=get('Spec Group Spec'); sh=[h.strip() for h in sgs[0]]
prot={}
for r in sgs[1:]:
    d=dict(zip(sh,r+['']*(len(sh)-len(r))))
    if d.get('SpecName','').strip().lower()=='protein':
        prot.setdefault(N(d.get('SpecGroupName2','')),(d.get('minimum','').strip(),d.get('maximum','').strip()))
sg=get('SpecGroup'); gh=[h.strip() for h in sg[0]]

def grade(mn,mx):
    a,b=flt(mn),flt(mx)
    if a is not None and abs(a-47)<0.01: return '47'
    if b is not None and abs(b-48)<0.01: return '47'
    if (a is not None and abs(a-45.5)<0.01) or (b is not None and abs(b-46.5)<0.01): return '46'
    return None  # 36% local or undetermined

rows=[]; plan=[]; skipped=[]
for r in sg[1:]:
    nm=dict(zip(gh,r)).get('name','')
    if 'SOYA' not in nm.upper(): continue
    key=N(nm)
    if key in fip_groups: continue          # already has FIP
    mn,mx=prot.get(key,('',''))
    g=grade(mn,mx)
    if not g: skipped.append((nm.strip(),f"{mn}-{mx}")); continue
    for lo,hi,fp in TPL[g]:
        rows.append([nm, 'Protein', lo, hi, fp])   # exact name verbatim
    plan.append((nm.strip(), g, f"{mn}-{mx}"))

print(f"groups getting FIP={len(plan)} | new FIP rows={len(rows)}")
for nm,g,band in plan: print(f"   [{g}%] {nm:64} (protein {band})")
print(f"excluded (no template): {skipped}")

# backup + append
with open(f"{BK}/SpecGroupFIP.csv",'w',newline='') as f: csv.writer(f).writerows(fip)
retry(lambda: svc.spreadsheets().values().append(spreadsheetId=SID,range="'SpecGroupFIP'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows}).execute())
print(f"SpecGroupFIP appended: {len(fip)-1} -> {len(fip)-1+len(rows)} rows (backup recon/backup/SpecGroupFIP.csv)")
cur=get('RECON 300626 - Applied')
note=[['PASS 2 SpecGroupFIP go-live 2026-07-01', f'{len(plan)} groups / {len(rows)} FIP rows ('+", ".join(f"{n} {g}%" for n,g,_ in plan)+')']]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
print("audited.")
