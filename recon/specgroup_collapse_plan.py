# -*- coding: utf-8 -*-
"""PLAN ONLY (no live changes): collapse jayson spec groups to one-per-raw-block. Parse the 68 raw
blocks, DEDUPE the 2 draft copies + drop packing-text origins, union spec lines, propose a collapsed
group per distinct (product, origins). Map each to the current jayson groups it would replace. Writes
review tab 'RECON SpecGroup Collapse Plan'. READ-ONLY."""
import glob, re, time
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def is_pack(o):  # packing/instruction text stacked in the Origin column - not a real origin
    u=str(o).upper(); return any(t in u for t in ('IN BULK','CONTAINER','20FT','40FT','RESERVED','DISABLED','GTMS'))
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,mn,mx=gi('SpecGroupName2'),gi('SpecGroupName3 (Origin)'),gi('SpecGroupName4 (Seller)'),gi('SpecName'),gi('minimum'),gi('maximum')
blocks=[]; cur=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p): cur={'product':norm(p),'region':'','origins':set(),'sellers':set(),'specs':[]}; blocks.append(cur)
    if cur is None: continue
    if O>=0 and row[O].strip():
        ov=norm(row[O]); u=ov.upper()
        if '(WM)' in u: cur.setdefault('region','WEST MALAYSIA')
        elif '(EM)' in u: cur.setdefault('region','EAST MALAYSIA')
        elif not banner(ov) and not is_pack(ov) and not ov.startswith('('): cur['origins'].add(ov)
    if S>=0 and row[S].strip() and not banner(row[S]): cur['sellers'].add(norm(row[S]))
    if SN>=0 and row[SN].strip() and ((mn>=0 and row[mn].strip()) or (mx>=0 and row[mx].strip())): cur['specs'].append(norm(row[SN]))
# dedupe: merge blocks with same (product, origins-set)
merged={}
for b in blocks:
    key=(nk(b['product']), b.get('region',''), frozenset(nk(o) for o in b['origins']), frozenset(nk(s2) for s2 in b['sellers']))
    m=merged.setdefault(key,{'product':b['product'],'region':b.get('region',''),'origins':set(),'sellers':set(),'specs':set(),'nblk':0})
    m['origins']|=b['origins']; m['sellers']|=b['sellers']; m['specs']|=set(b['specs']); m['nblk']+=1
print(f"raw blocks={len(blocks)} -> distinct collapsed groups (product x origins) = {len(merged)}")
# map to current jayson groups by product token
jsg=getj('SpecGroup'); jni=[c.strip() for c in jsg[0]].index('name')
jgroups=[norm(x[jni]) for x in jsg[1:] if len(x)>jni and x[jni].strip()]
from collections import Counter as _C
_poc=_C((k[0],k[1],k[2]) for k in merged)  # (product,region,origins) -> how many seller-variants
def proposed_name(key,m):
    region=m['region']; origins=' / '.join(sorted(m['origins'])) if m['origins'] else ('' if region else 'LOCAL')
    seller=''
    if _poc[(key[0],key[1],key[2])]>1 and m['sellers']:  # origin doesn't distinguish -> add seller
        seller=sorted(m['sellers'])[0]
    return ' '.join(x for x in [region, seller, origins, m['product']] if x).strip()
rows=[['proposed_group','product','origins','sellers','n_spec_lines','#raw_blocks_merged','current_jayson_groups_it_replaces']]
for key,m in sorted(merged.items(), key=lambda kv: kv[1]['product']):
    pk=key[0]; repl=[g for g in jgroups if pk in nk(g)]
    rows.append([proposed_name(key,m), m['product'], ', '.join(sorted(m['origins']))[:70], ', '.join(sorted(m['sellers']))[:70],
                 len(m['specs']), m['nblk'], ' | '.join(repl)[:150]])
title='RECON SpecGroup Collapse Plan'
meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=JAY).execute())
if title not in [s['properties']['title'] for s in meta['sheets']]:
    retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
print(f"wrote '{title}': {len(rows)-1} proposed collapsed groups (from {len(blocks)} raw blocks) vs current {len(jgroups)} jayson groups")
for row in rows[1:]: print(f"   {row[0][:44]:44} specs={row[4]} blks={row[5]} replaces={row[6][:40]}")
