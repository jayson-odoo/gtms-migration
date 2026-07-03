# -*- coding: utf-8 -*-
"""Block-level SpecGroup comparison: treat each raw SpecGroup block as a spec group and match it to
jayson spec groups by product + origin + seller tokens. Reports per-block matched jayson group(s) or
UNMATCHED, and jayson groups matched by no block. Writes 'VALIDATION SpecGroup Blocks'. READ-ONLY."""
import glob, re, time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openpyxl
KEY='/home/src/gen-lang-client-0473500312-692604319c2e.json'; JAY='1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U'; D='/home/src/raw_master/300626'
def nk(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
def norm(s): return re.sub(r'\s+',' ',str(s)).strip()
def banner(s):
    u=str(s).upper(); return any(t in u for t in ('SDN BHD','PTE LTD','QL FEED','QL INTERNATIONAL','ALL SELLERS'))
def retry(fn):
    for _ in range(8):
        try: return fn()
        except HttpError as e:
            if getattr(e,'resp',None) is not None and e.resp.status==429: time.sleep(25); continue
            raise
svc=build('sheets','v4',credentials=Credentials.from_service_account_file(KEY,scopes=['https://www.googleapis.com/auth/spreadsheets']),cache_discovery=False)
def getj(t): return retry(lambda: svc.spreadsheets().values().get(spreadsheetId=JAY,range=f"'{t}'").execute()).get('values',[])
# parse raw blocks
f=[x for x in glob.glob(f'{D}/*.xlsx') if 'Master Data (Part 1) 20260629' in x][0]
wb=openpyxl.load_workbook(f,read_only=True,data_only=True); ws=wb['SpecGroup']
r=[[('' if c.value is None else str(c.value).strip()) for c in row] for row in ws.iter_rows()]
h=[norm(x) for x in r[0]]
def gi(n): return next((i for i,x in enumerate(h) if nk(x)==nk(n)),-1)
P,O,S,SN,mn,mx=gi('SpecGroupName2'),gi('SpecGroupName3 (Origin)'),gi('SpecGroupName4 (Seller)'),gi('SpecName'),gi('minimum'),gi('maximum')
blocks=[]; cur=None
for row in r[1:]:
    row=row+['']*(len(h)-len(row)); p=row[P].strip()
    if p and not banner(p): cur={'product':p,'origins':set(),'sellers':set(),'nspec':0}; blocks.append(cur)
    if cur is None: continue
    if O>=0 and row[O].strip() and not banner(row[O]) and not row[O].strip().startswith('('): cur['origins'].add(norm(row[O]))
    if S>=0 and row[S].strip() and not banner(row[S]): cur['sellers'].add(norm(row[S]))
    if SN>=0 and row[SN].strip() and ((mn>=0 and row[mn].strip()) or (mx>=0 and row[mx].strip())): cur['nspec']+=1
jsg=getj('SpecGroup'); jni=[c.strip() for c in jsg[0]].index('name')
jgroups=[norm(r[jni]) for r in jsg[1:] if len(r)>jni and r[jni].strip()]
jnk={g:nk(g) for g in jgroups}
STOP={'MOLD','INHIBITOR','BEAN','MEAL','GRAIN','GRAINS','WITH','SOLUBLES','DRIED','DISTILLERS'}  # generic tokens
def toks(s): return {t for t in re.split(r'[^A-Za-z0-9]+',str(s).upper()) if len(t)>2 and t not in STOP}
rows=[['#','raw product','origins','sellers','n_specs','matched_jayson_groups','count','status']]
matched_groups=set(); nun=0
for i,b in enumerate(blocks,1):
    pk=nk(b['product'])
    cand=[g for g,gk in jnk.items() if pk in gk]           # product present in jayson group name
    # refine by origin/seller when the block names them
    otk=set().union(*[toks(o) for o in b['origins']]) if b['origins'] else set()
    stk=set().union(*[toks(s) for s in b['sellers']]) if b['sellers'] else set()
    refined=[g for g in cand if (not otk or otk & toks(g)) or (stk and stk & toks(g))] if (otk or stk) else cand
    use=refined if refined else cand
    for g in use: matched_groups.add(g)
    st='MATCHED' if use else ('PRODUCT-ONLY' if cand else 'UNMATCHED')
    if not use: nun+=1
    rows.append([i,b['product'],', '.join(sorted(b['origins']))[:60],', '.join(sorted(b['sellers']))[:60],b['nspec'],
                 ' | '.join(use[:4])[:120],len(use),st])
# jayson groups matched by no block
unmatched_j=[g for g in jgroups if g not in matched_groups]
rows.append([]); rows.append(['JAYSON GROUPS NOT MATCHED BY ANY RAW BLOCK:',len(unmatched_j)])
for g in unmatched_j: rows.append(['',g])
print(f"raw blocks={len(blocks)} | jayson groups={len(jgroups)} | blocks unmatched={nun} | jayson groups unmatched={len(unmatched_j)}")
title='VALIDATION SpecGroup Blocks'
meta=retry(lambda: svc.spreadsheets().get(spreadsheetId=JAY).execute())
if title not in [s['properties']['title'] for s in meta['sheets']]:
    retry(lambda: svc.spreadsheets().batchUpdate(spreadsheetId=JAY,body={'requests':[{'addSheet':{'properties':{'title':title}}}]}).execute())
retry(lambda: svc.spreadsheets().values().clear(spreadsheetId=JAY,range=f"'{title}'").execute())
retry(lambda: svc.spreadsheets().values().update(spreadsheetId=JAY,range=f"'{title}'!A1",valueInputOption='RAW',body={'values':rows}).execute())
print(f"wrote '{title}' ({len(blocks)} blocks + {len(unmatched_j)} unmatched-jayson)")
# print the block table to console
for row in rows[1:1+len(blocks)]:
    print(f"  {row[0]:>2} {row[1][:30]:30} O=[{row[2][:24]}] cnt={row[6]} {row[7]}")
