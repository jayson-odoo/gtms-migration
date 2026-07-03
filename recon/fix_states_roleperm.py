# -*- coding: utf-8 -*-
"""Sheet edits: add Penang/MY seed to 'States'; add the 183 super-admin (role_id=1) seed pairs to
'Role Permission' so sheet=db. Backup + audit. Sheet-only (db state-dup delete is a separate script)."""
import re, csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from gtms_migration.utils.pg import get_connection
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
def nk(s): return re.sub(r'\s+',' ',str(s)).strip()
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
c=get_connection();cur=c.cursor()

# ---- States: add Penang/MY ----
v=get('States'); h=[x.strip() for x in v[0]]; ni=h.index('name'); ci=next(i for i,x in enumerate(h) if 'countr' in x.lower())
with open(f"{BK}/States.pre-penang.csv",'w',newline='') as f: csv.writer(f).writerows(v)
has=any((r+['']*(len(h)-len(r)))[ni].strip().upper()=='PENANG' and (r+['']*(len(h)-len(r)))[ci].strip().upper()=='MY' for r in v[1:])
if not has:
    row={'name':'Penang','country':'MY','is_active':'TRUE'}
    retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'States'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':[[row.get(cc,'') for cc in h]]}).execute())
    print("States: +Penang/MY")
else: print("States: Penang already present")

# ---- Role Permission: add 183 super-admin pairs ----
v=get('Role Permission'); h=[x.strip() for x in v[0]]
pc=next(k for k in h if 'perm' in k.lower() and 'name' in k.lower()); rc=next(k for k in h if 'role' in k.lower() and 'name' in k.lower())
pidc=next((k for k in h if k.lower()=='permission_id'),None); ridc=next((k for k in h if k.lower()=='role_id'),None); col1=next((k for k in h if k.lower().startswith('column')),None)
with open(f"{BK}/Role Permission.pre-superadmin.csv",'w',newline='') as f: csv.writer(f).writerows(v)
cur.execute("select name,id from permissions"); perm={nk(n):i for n,i in cur.fetchall()}; pid2name={i:n for n,i in perm.items()}
cur.execute("select name from roles where id=1"); sarole=cur.fetchone()[0]
sd=[dict(zip(h,r+['']*(len(h)-len(r)))) for r in v[1:] if any(str(x).strip() for x in r)]
sheet_sa={perm.get(nk(d[pc])) for d in sd if nk(d.get(rc,''))==nk(sarole)}
cur.execute("select permission_id from role_has_permissions where role_id=1"); dbsa=[r[0] for r in cur.fetchall()]
add=[]
for pid in dbsa:
    if pid in sheet_sa: continue
    pname=pid2name.get(pid)
    if not pname: continue
    d={pc:pname, rc:sarole}
    if pidc: d[pidc]=pid
    if ridc: d[ridc]=1
    if col1: d[col1]=pname+sarole
    add.append([d.get(cc,'') for cc in h])
if add:
    retry(lambda: svc.spreadsheets().values().append(spreadsheetId=JAY,range="'Role Permission'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':add}).execute())
print(f"Role Permission: +{len(add)} super-admin ({sarole}) seed pairs")
cur2=get('RECON 300626 - Applied')
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur2+[[]]+[['STATES+ROLEPERM EXACT 2026-07-02',f'+Penang/MY seed to States; +{len(add)} super-admin seed pairs to Role Permission. backups .pre-penang/.pre-superadmin.csv']]}).execute())
print("audited."); c.close()
