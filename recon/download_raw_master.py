# -*- coding: utf-8 -*-
"""Sync a Google Drive folder of raw dept master-data files into raw_master/300626/.

Downloads every uploaded file in the source folder to the LOCAL raw_master/300626/
directory (destination is always 300626, as requested). Native Google Sheets (e.g. the
Jayson working sheet / the extract sheet, which live in the same folder) are SKIPPED by
default — they aren't raw dept submissions; set GTMS_INCLUDE_SHEETS=1 to export them too.
Read-only on Drive.

Usage (inside the mage-ui container):
    python3 recon/download_raw_master.py                 # default folder '300626 Master Data'
    python3 recon/download_raw_master.py <FOLDER_ID>     # a different source folder
    GTMS_RAW_FOLDER_ID=<id> python3 recon/download_raw_master.py
    GTMS_INCLUDE_SHEETS=1 python3 recon/download_raw_master.py   # also export native Sheets
"""
import os
import sys
import io
import re

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

KEY = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS',
                     '/home/src/gen-lang-client-0473500312-692604319c2e.json')
# Default: the '300626 Master Data' Drive folder the dept files were submitted to.
DEFAULT_FOLDER = '1GeN2hKmsX1KOEJ9jCzDuG42BNFSPdvIh'
FOLDER_ID = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GTMS_RAW_FOLDER_ID', DEFAULT_FOLDER))
DEST = '/home/src/raw_master/300626'   # always 300626

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
GSHEET_MIME = 'application/vnd.google-apps.sheet'
FOLDER_MIME = 'application/vnd.google-apps.folder'

drive = build('drive', 'v3', credentials=Credentials.from_service_account_file(
    KEY, scopes=['https://www.googleapis.com/auth/drive.readonly']), cache_discovery=False)


def safe(name):
    name = re.sub(r'[\\/:*?"<>|]+', '_', name).strip()
    return name if name.lower().endswith(('.xlsx', '.xls', '.csv')) else name + '.xlsx'


def list_folder(folder_id):
    files, token = [], None
    while True:
        resp = drive.files().list(
            q="'%s' in parents and trashed = false" % folder_id,
            fields='nextPageToken, files(id, name, mimeType, modifiedTime)',
            pageSize=200, pageToken=token,
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        files.extend(resp.get('files', []))
        token = resp.get('nextPageToken')
        if not token:
            break
    return files


def fetch(f):
    """Return (filename, bytes) for a Drive file; export native sheets to xlsx."""
    if f['mimeType'] == GSHEET_MIME:
        req = drive.files().export_media(fileId=f['id'], mimeType=XLSX_MIME)
    else:
        req = drive.files().get_media(fileId=f['id'], supportsAllDrives=True)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return safe(f['name']), buf.getvalue()


def main():
    meta = drive.files().get(fileId=FOLDER_ID, fields='name', supportsAllDrives=True).execute()
    os.makedirs(DEST, exist_ok=True)
    include_sheets = os.environ.get('GTMS_INCLUDE_SHEETS') == '1'
    all_files = [f for f in list_folder(FOLDER_ID) if f['mimeType'] != FOLDER_MIME]
    files = all_files if include_sheets else [
        f for f in all_files if not f['mimeType'].startswith('application/vnd.google-apps.')]
    skipped = len(all_files) - len(files)
    print("source folder %r (%s) -> %s" % (meta.get('name'), FOLDER_ID, DEST))
    print("found %d file(s)%s\n" % (
        len(files), '' if not skipped else ' (skipped %d native Google Sheet(s); GTMS_INCLUDE_SHEETS=1 to include)' % skipped))
    ok = 0
    for f in sorted(files, key=lambda x: x['name']):
        try:
            fname, data = fetch(f)
            with open(os.path.join(DEST, fname), 'wb') as fh:
                fh.write(data)
            print("  [OK]   %-55s %8.1f KB" % (fname[:55], len(data) / 1024))
            ok += 1
        except Exception as e:
            print("  [FAIL] %-55s %s" % (f['name'][:55], str(e)[:80]))
    print("\ndownloaded %d/%d file(s) into %s" % (ok, len(files), DEST))


if __name__ == '__main__':
    main()
