"""legal-entity / master_regions — data exporter (upsert).

INSERT ... ON CONFLICT (name) DO UPDATE SET is_active. The natural key is `name`
(there is a UNIQUE (name) constraint); `id` is dropped by upsert() so the sequence
assigns it and existing rows match by name (avoids PK clashes on a seeded prod DB).
"""
from gtms_migration.utils.pg import upsert

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

TABLE = 'master_regions'
CONFLICT_COLS = ['name']
UPDATE_COLS = ['is_active']


@data_exporter
def export_data(df, **kwargs):
    n = upsert(
        df, TABLE,
        conflict_cols=CONFLICT_COLS,
        update_cols=UPDATE_COLS,
        set_timestamps_on_insert=['created_at', 'updated_at'],
        backfill_timestamps=['created_at', 'updated_at'],
    )
    print(f'[{TABLE}] upserted {n} rows (conflict={CONFLICT_COLS}, update={UPDATE_COLS})')
    return df  # pass the cleaned sheet rows to the downstream validator
