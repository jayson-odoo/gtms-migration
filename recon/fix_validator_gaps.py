# -*- coding: utf-8 -*-
"""Make 3 validators reconcile: dedup 'States' (CI name+country) + 'Role Permission' (CI perm+role),
and add the 2 pre-existing prod seed snippets to 'Document Content Snippet'. Backup + audit. Sheet-only."""
import re, csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
def ci(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
def rewrite(t, rows):
    retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{t}'").execute())
    retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{t}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
def backup(t,v):
    with open(f"{BK}/{t}.pre-vgap.csv",'w',newline='') as f: csv.writer(f).writerows(v)

def dedup(tab, keycols):
    v=get(tab); h=[c.strip() for c in v[0]]; idx=[next(i for i,c in enumerate(h) if c.strip().lower()==k.lower()) for k in keycols]
    backup(tab,v); out=[h]; seen=set(); dropped=0
    for r in v[1:]:
        r=r+['']*(len(h)-len(r))
        if not any(x.strip() for x in r): continue
        key=tuple(ci(r[i]) for i in idx)
        if all(k=='' for k in key): out.append(r); continue
        if key in seen: dropped+=1; continue
        seen.add(key); out.append(r)
    rewrite(tab,out); print(f"{tab}: {len(v)-1} -> {len(out)-1} rows (dropped {dropped} dup on {keycols})")

dedup('States', ['name','country'])
dedup('Role Permission', ['permission_name','role_name'])

# add 2 seed snippets
t='Document Content Snippet'; v=get(t); h=[c.strip() for c in v[0]]; backup(t,v)
SEED=[{'name':'Invoice Remarks','printout_description':'Please communicate with us within 7 (seven) days from the date of this invoice should you\ndisagree with it.\nPayment by cheque should be crossed and made payable to QL FEED SDN. BHD.\nWe reserve the right to charge interest at the rate of 1.5% per month on overdue accounts.','document_template_id':'BILLING_DOCUMENT','is_active':'TRUE'},
      {'name':'Pricing Approved By','printout_description':'Chia Song Swa','document_template_id':'PRICING','is_active':'TRUE'}]
existing={ci(r[h.index('name')]) for r in v[1:] if len(r)>h.index('name')}
add=[[s.get(c,'') for c in h] for s in SEED if ci(s['name']) not in existing]
if add:
    retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range=f"'{t}'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':add}).execute())
print(f"{t}: +{len(add)} seed snippet rows (Invoice Remarks/Pricing Approved By)")
cur=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+[['VALIDATOR GAP FIXES 2026-07-02','States dedup (CI name+country), Role Permission dedup (CI perm+role), +2 seed snippets. backups *.pre-vgap.csv']]}).execute())
print("audited.")
