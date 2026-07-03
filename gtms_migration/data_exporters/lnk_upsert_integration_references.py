"""linkages / master_integration_references — exporter (full refresh).

This table is regenerated wholesale from the Integration Reference sheet (itself derived
from Counterparty v2). A merged vendor+customer counterparty yields TWO rows that share the
same integratable_id, so an upsert keyed on the record would collapse them. Instead we do a
full refresh per external system: delete the existing references, then insert the fresh set.
Also clears the old wrong-format (forward-slash) integratable_type rows.
"""
from datetime import datetime, timezone

import pandas as pd
from psycopg2.extras import execute_values

from gtms_migration.utils.pg import get_connection, _py

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

TABLE = 'master_integration_references'
COLS = ['integratable_type', 'integratable_id', 'external_system_id',
        'vendor_reference_no', 'customer_reference_no', 'created_at', 'updated_at']


@data_exporter
def export_data(df, **kwargs):
    out = df[df['integratable_id'].notna() & df['external_system_id'].notna()].copy()
    skipped = len(df) - len(out)
    if skipped:
        print(f'[{TABLE}] skipping {skipped} row(s) with unresolved counterparty/external_system')

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out['created_at'] = now
    out['updated_at'] = now
    es_ids = [int(x) for x in out['external_system_id'].dropna().unique()]
    rows = [tuple(_py(r[c]) for c in COLS) for _, r in out.iterrows()]

    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(f'DELETE FROM {TABLE} WHERE external_system_id = ANY(%s)', (es_ids,))
            deleted = cur.rowcount
            col_sql = ', '.join(f'"{c}"' for c in COLS)
            execute_values(cur, f'INSERT INTO {TABLE} ({col_sql}) VALUES %s', rows, page_size=1000)
        print(f'[{TABLE}] full refresh: deleted {deleted}, inserted {len(rows)}')
    finally:
        conn.close()
    return df
