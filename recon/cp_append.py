# -*- coding: utf-8 -*-
import csv, re
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
BK='/home/src/recon/backup'
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return svc.spreadsheets().values().get(spreadsheetId=SID,range=f"'{t}'").execute().get('values',[])

prev=get('RECON 300626 - CPv2 Adds')
phdr=[h.strip() for h in prev[2]]; pdata=prev[3:]
cv=get('Counterparty v2'); chdr=[h.strip() for h in cv[0]]
assert phdr==chdr, f"header mismatch:\n{phdr}\n{chdr}"
# backup current state (post-rename, pre-append)
with open(f"{BK}/Counterparty v2.pre-append.csv",'w',newline='') as fp: csv.writer(fp).writerows(cv)
before=len(cv)-1
# pad rows to header width
rows=[ (r+['']*len(chdr))[:len(chdr)] for r in pdata ]
svc.spreadsheets().values().append(spreadsheetId=SID, range="'Counterparty v2'",
    valueInputOption='RAW', insertDataOption='INSERT_ROWS', body={'values':rows}).execute()
cv2=get('Counterparty v2'); after=len(cv2)-1
mi=chdr.index('M3 Code')
codes={r[mi].strip() for r in cv2[1:] if mi<len(r)}
NEW=['QBUNG002QF','QCARG003QF','QFYSD001QF','QGRAI001QI','QHONG001QI','QJCSU001QF','QNUSA001QI','QPTTO001QI','QQLLP001QF','QSUCR001QF','QTGLU001QI','QVIAT001QF','QWHEA001QI']
print(f"Counterparty v2 rows: {before} -> {after} (+{after-before})")
print("present:", all(c in codes for c in NEW), "| missing:", [c for c in NEW if c not in codes])
# audit
title='RECON 300626 - Applied'; cur=get(title)
log=cur+[[]]+[['PASS 2 Counterparty v2 appends 2026-07-01','','']]+[['M3 Code added']]+[[c] for c in NEW]
svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':log}).execute()
print("backup -> recon/backup/Counterparty v2.pre-append.csv ; audit updated")
