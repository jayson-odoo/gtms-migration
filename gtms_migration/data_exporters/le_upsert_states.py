"""legal-entity / master_states — data exporter (upsert).

KNIME node: DB Merger (#16) -> table master_states.
  match (WHERE) columns : name, country
  update (SET) columns  : is_active
master_states has no unique index on (name, country), so we use the per-row
UPDATE-then-INSERT mode (matches the DB Merger exactly, no constraint required).
"""
from gtms_migration.utils.pg import read_sql, upsert

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

TABLE = 'master_states'
CONFLICT_COLS = ['name', 'country']
UPDATE_COLS = ['is_active']


@data_exporter
def export_data(df, **kwargs):
    # country is a FK to master_countries(code); skip states whose country doesn't
    # exist (otherwise the insert violates master_states_country_foreign). The
    # validator reports these. The full df is returned downstream for validation.
    valid = set(read_sql('select code from master_countries')['code'].astype(str))
    ok = df['country'].astype(str).isin(valid)
    if (~ok).any():
        bad = sorted(df.loc[~ok, 'country'].astype(str).unique())
        print(f'[{TABLE}] skipping {int((~ok).sum())} row(s) with non-existent country: {bad}')

    n = upsert(
        df[ok], TABLE,
        conflict_cols=CONFLICT_COLS,
        update_cols=UPDATE_COLS,
        set_timestamps_on_insert=['created_at', 'updated_at'],
        backfill_timestamps=['created_at', 'updated_at'],
        mode='update_insert',
    )
    print(f'[{TABLE}] upserted {n} rows (conflict={CONFLICT_COLS}, update={UPDATE_COLS})')
    return df
