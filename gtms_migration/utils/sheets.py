"""Google Sheets reader for the GTMS migration.

Reads a worksheet tab from the source spreadsheet using a service-account
credential. Returns a pandas DataFrame where the first sheet row is the header
and every cell is a string (matching how KNIME's Google Sheets Reader hands the
data downstream — type coercion happens in the transformer blocks).
"""
import os

import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Read + write (validator tabs are written back). Service account needs Editor access.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def _service():
    key_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)


def _sid(spreadsheet_id=None):
    return spreadsheet_id or os.environ['GSHEET_ID']


def _tab_titles(svc, spreadsheet_id):
    meta = svc.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return [s['properties']['title'] for s in meta['sheets']]


def _ensure_tab(svc, spreadsheet_id, tab_name):
    if tab_name not in _tab_titles(svc, spreadsheet_id):
        svc.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{'addSheet': {'properties': {'title': tab_name}}}]},
        ).execute()


def _df_to_values(df: pd.DataFrame):
    """Header + rows as JSON-serialisable strings (Sheets rejects NaN/Timestamp)."""
    def _cell(v):
        # list/array cells (e.g. a JSON array column like profit_centers) aren't scalar -> pd.isna
        # returns an array and breaks the truthiness check; stringify them directly.
        if isinstance(v, (list, tuple, set, dict)):
            return str(v)
        return '' if pd.isna(v) else str(v)
    header = [list(map(str, df.columns))]
    body = [[_cell(v) for v in row] for row in df.itertuples(index=False, name=None)]
    return header + body


def overwrite_tab(tab_name: str, df: pd.DataFrame, spreadsheet_id=None):
    """Clear a tab and write the DataFrame (header + rows) starting at A1."""
    svc = _service()
    sid = _sid(spreadsheet_id)
    _ensure_tab(svc, sid, tab_name)
    svc.spreadsheets().values().clear(spreadsheetId=sid, range=f"'{tab_name}'").execute()
    svc.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"'{tab_name}'!A1",
        valueInputOption='RAW',
        body={'values': _df_to_values(df)},
    ).execute()


def upsert_row_count_validator(table: str, check_name: str, passed: bool, justification: str,
                               tab_name: str = 'Row Count Validator', spreadsheet_id=None,
                               checked_at: str = ''):
    """Update (or append) this check's row in the shared Row Count Validator tab.

    Schema: [master data, row count valid, justification, table, checked_at]. The row is
    matched on `master data` (the unique check_name) so each pipeline maintains exactly one
    line — keyed by check_name, NOT table, because one physical table can be written by two
    different checks (e.g. master_counterparties <- is_profit_centers_passed + is_counterparty_v2_passed).
    Rows from the older 4-column layout are padded/upgraded in place.
    """
    svc = _service()
    sid = _sid(spreadsheet_id)
    _ensure_tab(svc, sid, tab_name)
    rows = (
        svc.spreadsheets().values().get(spreadsheetId=sid, range=f"'{tab_name}'").execute().get('values', [])
    )
    header = ['master data', 'row count valid', 'justification', 'table', 'checked_at']
    width = len(header)
    if not rows:
        rows = [header]
    else:
        rows[0] = header  # upgrade header (old layout had no checked_at column)
    new_row = [check_name, str(bool(passed)).lower(), justification, table, checked_at]
    found = False
    for i in range(1, len(rows)):
        r = rows[i] + [''] * (width - len(rows[i]))  # pad legacy 4-col rows
        if r[0] == check_name and not found:  # match on the unique check_name (col A)
            rows[i] = new_row
            found = True
        else:
            rows[i] = r
    if not found:
        rows.append(new_row)
    svc.spreadsheets().values().clear(spreadsheetId=sid, range=f"'{tab_name}'").execute()
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range=f"'{tab_name}'!A1", valueInputOption='RAW', body={'values': rows},
    ).execute()


def read_tab(sheet_name: str, spreadsheet_id: str = None) -> pd.DataFrame:
    """Read a worksheet tab into a DataFrame (header = first row, values = str)."""
    spreadsheet_id = spreadsheet_id or os.environ['GSHEET_ID']
    svc = _service()
    rng = f"'{sheet_name}'"  # whole sheet; quoting handles tab names with spaces
    resp = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=rng, valueRenderOption='FORMATTED_VALUE')
        .execute()
    )
    rows = resp.get('values', [])
    if not rows:
        return pd.DataFrame()
    header, *body = rows
    # Normalize every row to the header width: pad short rows (Sheets omits trailing empty
    # cells) AND truncate over-wide rows (a stray unheadered column otherwise crashes the
    # DataFrame build and fails the whole pipeline).
    width = len(header)
    body = [(r + [''] * (width - len(r)))[:width] for r in body]
    df = pd.DataFrame(body, columns=header)
    return df.astype(str)
