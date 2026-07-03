# -*- coding: utf-8 -*-
"""READ-ONLY delta: parse raw 'Additional Charges' hierarchical draft -> (section, group, name,
price, charges_type); diff names vs live 'Additonal Costs' (230). Write review tab
'RECON 300626 - Charges Candidates'. NO writes to Additonal Costs."""
import re, time
import openpyxl
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; SID='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'
DIR='/home/src/raw_master/300626'; PUR='Purchasing QL Feed  QL International - QL Master Data (Part 1) 20260629.xlsx'
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def N(s): return re.sub(r'\s+',' ',str(s)).strip().upper()
def isnum(s):
    try: float(str(s)); return True
    except: return False
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def get(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=SID,range=f"'{t}'").execute()).get('values',[])

# live names + default_value + group
adc=get('Additonal Costs'); h=[c.strip() for c in adc[0]]
ni=h.index('name'); dvi=h.index('default_value'); gi=h.index('additional cost group')
def g(r,i): return r[i].strip() if len(r)>i else ''
live={N(g(r,ni)) for r in adc[1:] if g(r,ni)}
live_dv={N(g(r,ni)):g(r,dvi) for r in adc[1:] if g(r,ni)}
live_grp={N(g(r,ni)):g(r,gi) for r in adc[1:] if g(r,ni)}

wb=openpyxl.load_workbook(f"{DIR}/{PUR}", data_only=True)
ws=wb['Additional Charges']
def cell(row,i):
    v=row[i].value if len(row)>i else None
    return '' if v is None else str(v).strip()
def bold(row,i):
    c=row[i] if len(row)>i else None
    return bool(c and c.font and c.font.bold)

section=''; group=''; items=[]
# cols: A=0 id/num, B=1 Name, C=2 Description(empty), D=3 Charges Type, E=4 Unit Price
GRPCLEAN=lambda s: re.sub(r'\s*\((if any|for.*?)\)\s*$','',s,flags=re.I).strip()
for row in ws.iter_rows(min_row=2):
    a,b,d,e=cell(row,0),cell(row,1),cell(row,3),cell(row,4)
    # section / cargo-handler / remark headers -> reset group
    if (b and bold(row,1) and 'IMPORT EXPENSES' in b.upper()) or 'CARGO HANDLER' in (a+b).upper() or (a+b).upper().startswith('REMARK'):
        section = b or a; group=''; continue
    # group header: col A is a letter (a./b./c.) with a bold name in col B
    if re.fullmatch(r'[a-z]\.', a) and b:
        group=GRPCLEAN(b); continue
    # line item: numbered, has a name, sits under a group
    if isnum(a) and b and group:
        price=e if isnum(e) else ''
        items.append(dict(section=section, group=group, name=b, price=price, charges_type=d))

# dedupe by name (live key is name) - flag conflicts
byname={}
for it in items:
    k=N(it['name']); byname.setdefault(k,[]).append(it)
def fnum(s):
    try: return float(str(s))
    except: return None
rows=[]; new=0; diff=0; conflict_n=0
for k,lst in byname.items():
    it=lst[0]
    in_live = k in live
    if not in_live: new+=1
    rprices=sorted({x['price'] for x in lst if x['price']!=''})
    lv=live_dv.get(k,'')
    # status
    if not in_live:
        status='NEW'
    elif len(rprices)>1:
        status='RAW-PRICE-CONFLICT '+"/".join(rprices); conflict_n+=1
    elif rprices and fnum(rprices[0]) is not None and fnum(lv) is not None and abs(fnum(rprices[0])-fnum(lv))>1e-6:
        status=f'PRICE DIFF raw={rprices[0]} live={lv}'; diff+=1
    elif rprices and not lv:
        status=f'live blank; raw={rprices[0]}'; diff+=1
    else:
        status='match'
    rawp=rprices[0] if len(rprices)==1 else "/".join(rprices)
    rows.append(['' if in_live else 'Y', it['group'], it['name'], rawp, lv, live_grp.get(k,''), it['charges_type'], status, it['section']])

order={'NEW':0}
rows.sort(key=lambda r:(0 if r[7]=='NEW' else 1 if r[7].startswith('PRICE DIFF') else 2 if 'CONFLICT' in r[7] else 3, r[1], r[2]))
print(f"parsed line-items={len(items)} | distinct names={len(byname)} | NEW={new} | PRICE DIFFs={diff} | raw-price-conflicts={conflict_n}")
print("\nPRICE DIFFERENCES (name exists in live, raw price != live default_value):")
for r in rows:
    if r[7].startswith('PRICE DIFF') or r[7].startswith('live blank'):
        print(f"   [{r[1]:30}] {r[2][:40]:40} {r[7]}")
print("\nRAW-PRICE-CONFLICTS (same name, multiple raw prices - can't auto-pick):")
for r in rows:
    if 'CONFLICT' in r[7]:
        print(f"   {r[2][:44]:44} {r[7]}  (live={r[4]})")

title='RECON 300626 - Charges Candidates'
meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=SID).execute())
if title not in [s['properties']['title'] for s in meta['sheets']]:
    retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=SID,range=f"'{title}'").execute())
hdr=['apply (Y/N)','raw group','name','raw price','live default_value','live group','charges_type','status','raw section']
note=[f'READ-ONLY review. NEW={new}, PRICE-DIFFs={diff}, raw-price-conflicts={conflict_n}. All 102 raw names already exist in live Additonal Costs. Mark apply=Y on any price-diff you want pushed to live default_value, then tell me. Defaults for NEW (none here): value_type=absolute, profit_centers=QL Feed+QL International, contract_types=["1"], is_active=TRUE.']
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=SID,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':[note,[],hdr]+rows}).execute())
print(f"\nwrote review tab '{title}' ({len(rows)} rows)")
