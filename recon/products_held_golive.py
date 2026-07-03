# -*- coding: utf-8 -*-
# Append the 7 held products with user-confirmed GTMS Packing Unit mappings.
# BAG->50KG_PP (x4), TOTES->TOTE_20FT_C, DRUM->SD_40FT_C. default_uom already MT.
import csv, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; BK='/home/src/recon/backup'
PU={'TGQDMXPL':'TOTE_20FT_C','TGQFM55':'50KG_PP','TGQSFOR':'SD_40FT_C','TGQSFOC':'SD_40FT_C',
    'TGQWBP':'50KG_PP','TGQSBMFF':'50KG_PP','TGQDLM':'50KG_PP'}
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
bg=retry(lambda: svc.spreadsheets().values().batchGet(spreadsheetId=SID, ranges=["'Products'","'RECON 300626 - Products NEW'"]).execute())['valueRanges']
pv=bg[0].get('values',[]); ph=[h.strip() for h in pv[0]]
sv=bg[1].get('values',[]); sh=[h.strip() for h in sv[2]]; sdata=sv[3:]
# re-backup CURRENT Products (state includes the earlier +13) so this append is independently reversible
with open(f"{BK}/Products.pre-held.csv",'w',newline='') as f: csv.writer(f).writerows(pv)
existing=set(str(r[0]).strip().upper() for r in pv[1:] if r)  # guard against double-append
rows=[]; skipped=[]
for r in sdata:
    d=dict(zip(sh, r+['']*(len(sh)-len(r))))
    code=d.get('code','').strip().upper()
    if code not in PU: continue
    if code in existing: skipped.append(code); continue
    d['GTMS Packing Unit']=PU[code]
    rows.append([d.get(h,'') for h in ph])
assert len(rows)+len(skipped)==len(PU), f"expected {len(PU)} held, matched {len(rows)+len(skipped)}"
if rows:
    retry(lambda: svc.spreadsheets().values().append(spreadsheetId=SID,range="'Products'",valueInputOption='RAW',insertDataOption='INSERT_ROWS',body={'values':rows}).execute())
print(f"Products held appended: {len(rows)} (rows {len(pv)-1}->{len(pv)-1+len(rows)}) | already-present skipped: {skipped}")
for row in rows: print("   ", dict(zip(ph,row)).get('code'), '->', dict(zip(ph,row)).get('GTMS Packing Unit'))
# reflect packing unit back into staging tab for an accurate record
puidx=sh.index('GTMS Packing Unit')
newsv=[sv[0],sv[1],sv[2]]
for r in sdata:
    r=r+['']*(len(sh)-len(r)); code=r[sh.index('code')].strip().upper()
    if code in PU: r[puidx]=PU[code]
    newsv.append(r)
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range="'RECON 300626 - Products NEW'!A1",valueInputOption='RAW',body={'values':newsv}).execute())
# audit
cur=retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range="'RECON 300626 - Applied'").execute()).get('values',[])
note=[['PASS 2 Products HELD go-live 2026-07-01', f'{len(rows)} added w/ packing units: '+", ".join(f"{c}={PU[c]}" for c in PU if c not in skipped)]]
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range="'RECON 300626 - Applied'!A1",valueInputOption='RAW',body={'values':cur+[[]]+note}).execute())
print("backed up recon/backup/Products.pre-held.csv + staging updated + audited")
