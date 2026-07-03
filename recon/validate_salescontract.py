# -*- coding: utf-8 -*-
"""Compare raw GTMS_SC (sales contract source) vs Jayson. Product Spec_SC vs SpecGroup.
sales_spec_group_description; QLF/QLI clauses vs Document Content Snippet. Writes report tabs."""
import io, re, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; FID='12HJ4fHGWk50KeGpJW3NYV2O3pZOop_EV'
creds=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/spreadsheets'])
drive=build('drive','v3',credentials=creds,cache_discovery=False); sheets=build('sheets','v4',credentials=creds,cache_discovery=False)
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def getj(t): return retry(lambda: sheets.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
buf=io.BytesIO(); dl=MediaIoBaseDownload(buf, drive.files().get_media(fileId=FID)); d=False
while not d: _,d=dl.next_chunk()
buf.seek(0); wb=openpyxl.load_workbook(buf, data_only=True, read_only=True)
def rowsof(t): ws=wb[t]; return [[('' if c.value is None else str(c.value).strip()) for c in r] for r in ws.iter_rows()]
# ---- Product Spec_SC: parse product blocks -> spec text ----
ps=rowsof('Product Spec_SC'); prodblocks=[]; cur=None
for r in ps:
    r=r+['']*(3-len(r))
    if r[0].strip(): cur={'product':r[0].strip(),'lines':[]}; prodblocks.append(cur)
    elif cur is not None and (r[1].strip() or r[2].strip()):
        cur['lines'].append((r[1].strip()+' '+r[2].strip()).strip())
def prodcore(s):
    u=s.upper()
    for w in ['ARGENTINA','BRAZILLIAN','BRAZILIAN','BRAZIL','U.S.','US','U. S.','UNITED STATES','CHINA','AUSTRALIAN','AUSTRALIA','LOCAL','EXPORT','CHILE','INDIA']:
        u=u.replace(w,' ')
    return nk(u)
# Jayson spec groups + sales desc
sg=getj('SpecGroup'); sh=[x.strip() for x in sg[0]]; sgi=sh.index('sales_spec_group_description'); ni=sh.index('name')
jgroups=[(r[ni].strip(), (r[sgi].strip() if len(r)>sgi else '')) for r in sg[1:] if len(r)>ni and r[ni].strip()]
sc_summary=[['raw product (Product Spec_SC)','#spec lines','matched jayson groups','groups w/ salesdesc','finding']]
unmatched=[]
for b in prodblocks:
    pc=prodcore(b['product'])
    matched=[g for g,sd in jgroups if prodcore(g)==pc or (pc and pc in prodcore(g))]
    withdesc=sum(1 for g in matched for gg,sd in jgroups if gg==g and sd.strip())
    if not matched: unmatched.append(b['product'])
    sc_summary.append([b['product'], len(b['lines']), len(matched), withdesc,
                       'no jayson group match' if not matched else ('OK - has salesdesc' if withdesc else 'matched but salesdesc BLANK')])
# ---- Clauses vs Document Content Snippet ----
def clause_cats(tab):
    r=rowsof(tab); cats=[]; cur=None
    for row in r:
        row=row+['']*(4-len(row))
        if row[0].strip(): cur=row[0].strip(); cats.append(cur)
    return cats
qlf=clause_cats('QLF_contract clauses'); qli=clause_cats('QLI_contract clauses')
dcs=getj('Document Content Snippet'); dch=[x.strip() for x in dcs[0]]
snip_names=[r[0].strip() for r in dcs[1:] if r and r[0].strip()]
clause_summary=[['source','clause category','in jayson snippet?']]
for c in qlf:
    hit=any(nk(c) in nk(s) for s in snip_names)
    clause_summary.append(['QLF', c, 'yes' if hit else 'NO'])
for c in qli:
    hit=any(nk(c) in nk(s) for s in snip_names)
    clause_summary.append(['QLI', c, 'yes' if hit else 'NO'])
print(f"### Product Spec_SC: {len(prodblocks)} products | unmatched to jayson group: {unmatched}")
print(f"### QLF clause categories={len(qlf)} | QLI clause categories={len(qli)} | existing jayson snippets={len(snip_names)}")
print("QLF cats:", qlf); print("QLI cats:", qli)
print("existing snippet names:", snip_names[:12])
def write(title, rows):
    meta=retry(lambda: sheets.spreadsheets().get(spreadsheetId=JAY).execute())
    if title not in [s['properties']['title'] for s in meta['sheets']]:
        retry(lambda: sheets.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
    retry(lambda: sheets.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
    retry(lambda: sheets.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
write('VALIDATION SalesContract Spec (Summary)', sc_summary)
write('VALIDATION SalesContract Clauses (Summary)', clause_summary)
print("\nwrote report tabs: SalesContract Spec + Clauses summaries")
