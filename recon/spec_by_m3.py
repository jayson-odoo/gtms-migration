# -*- coding: utf-8 -*-
"""Flatten the raw 'SpecGroup' tab into one row per spec line, with the M3 Code and GTMS
spec-group name forward-filled next to EVERY spec line (so each line is self-contained
'from the M3 perspective'). SpecName is filled down onto tier/continuation rows. Output:

  M3 Code | GTMS Spec Group | SpecName | SpecDescription | value_unit | value_type |
  minimum | maximum | minimum_basis | maximum_basis

Reads the Drive xlsx (SPEC_SID), writes recon/out/spec_by_m3.csv, and (GTMS_WRITE=1) writes
a 'Spec by M3' tab into the Jayson sheet (GSHEET_ID). Read-only on the source Drive file.
"""
import os, io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pandas as pd

KEY = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
SID = os.environ.get('SPEC_SID', '1fi09T_D7tW76xK06We0P5-stSsG0dtFx')
JAY = os.environ['GSHEET_ID']
OUT_TAB = 'Spec by M3'
TAB = 'SpecGroup'
OUT = '/home/src/recon/out/spec_by_m3.csv'

_scopes = ['https://www.googleapis.com/auth/drive.readonly',
           'https://www.googleapis.com/auth/spreadsheets']
_creds = Credentials.from_service_account_file(KEY, scopes=_scopes)
drive = build('drive', 'v3', credentials=_creds, cache_discovery=False)
sheets = build('sheets', 'v4', credentials=_creds, cache_discovery=False)
buf = io.BytesIO()
dl = MediaIoBaseDownload(buf, drive.files().get_media(fileId=SID))
done = False
while not done:
    _, done = dl.next_chunk()
buf.seek(0)
raw = pd.ExcelFile(buf).parse(TAB, header=None)

hdr = [str(x).strip() for x in raw.iloc[0].tolist()]
df = raw.iloc[1:].reset_index(drop=True)
df.columns = range(df.shape[1])

# Column positions (by the header row we just saw).
C_GTMS, C_DESC = 4, 5           # GTMS Name (spec-group anchor), SpecGroupDescription
C_SPEC = list(range(6, 14))     # SpecName..maximum_basis (the 8 spec-line columns)
C_M3 = 14                       # M3 Code (only on the anchor row)
SPEC_LABELS = ['SpecName', 'SpecDescription', 'value_unit', 'value_type',
               'minimum', 'maximum', 'minimum_basis', 'maximum_basis']


def val(x):
    s = '' if x is None else str(x).strip()
    return '' if s.lower() in ('nan', 'none', 'nat') else s


rows = []
cur_group, cur_m3, cur_spec = '', '', ''
for _, r in df.iterrows():
    gtms = val(r[C_GTMS])
    m3 = val(r[C_M3])
    if gtms:                     # new spec-group block starts here
        cur_group = gtms
        cur_spec = ''            # reset the running SpecName at each block
    if m3:                       # M3 restated -> update the running M3
        cur_m3 = m3
    spec = [val(r[c]) for c in C_SPEC]
    if not any(spec):
        continue                 # skip fully-empty rows
    # Fill SpecName down: a blank SpecName on a tier/continuation row inherits the
    # parent spec's name; a new non-blank SpecName resets it.
    if spec[0]:
        cur_spec = spec[0]
    else:
        spec[0] = cur_spec
    rows.append([cur_m3, cur_group] + spec)

out = pd.DataFrame(rows, columns=['M3 Code', 'GTMS Spec Group'] + SPEC_LABELS)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
out.to_csv(OUT, index=False)

print('parsed %d spec line(s) across %d spec group(s), %d distinct M3 code(s)'
      % (len(out), out['GTMS Spec Group'].nunique(), out['M3 Code'].replace('', pd.NA).nunique()))
print('\nspec lines per M3 Code:')
print(out.groupby(out['M3 Code'].replace('', '(none)')).size().to_string())
print('\n===== preview (first 25) =====')
with pd.option_context('display.max_rows', 25, 'display.max_columns', 20,
                       'display.width', 240, 'display.max_colwidth', 26):
    print(out.head(25).to_string(index=False))
print('\nwrote', OUT)

if os.environ.get('GTMS_WRITE') == '1':
    meta = sheets.spreadsheets().get(spreadsheetId=JAY).execute()
    tabs = [s['properties']['title'] for s in meta['sheets']]
    if OUT_TAB not in tabs:
        sheets.spreadsheets().batchUpdate(spreadsheetId=JAY, body={
            'requests': [{'addSheet': {'properties': {'title': OUT_TAB}}}]}).execute()
    sheets.spreadsheets().values().clear(spreadsheetId=JAY, range="'%s'" % OUT_TAB).execute()
    body = {'values': [list(out.columns)] + out.astype(str).values.tolist()}
    sheets.spreadsheets().values().update(
        spreadsheetId=JAY, range="'%s'!A1" % OUT_TAB,
        valueInputOption='RAW', body=body).execute()
    print("wrote %d rows to Jayson tab %r" % (len(out), OUT_TAB))
else:
    print('(dry-run; GTMS_WRITE=1 to also write the Jayson %r tab)' % OUT_TAB)
