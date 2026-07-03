"""legal-entity / master_countries — data exporter (upsert).

KNIME node: DB Merger (#11) -> table master_countries.
  match (WHERE) column : code
  update (SET) columns : name, is_active   (id is NOT changed on conflict)
Replicated as INSERT ... ON CONFLICT (code) DO UPDATE SET name, is_active.
"""
from gtms_migration.utils.pg import upsert

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

TABLE = 'master_countries'
CONFLICT_COLS = ['code']
UPDATE_COLS = ['name', 'is_active']


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
