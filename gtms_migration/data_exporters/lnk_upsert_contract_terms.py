"""linkages / master_contract_terms — exporter. Upsert on `name`.
mode defaults to update_insert (no unique-index requirement); switch to on_conflict if a
unique index on name is confirmed."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

UPDATE_COLS = ['basis_weight', 'description', 'fulfillment_tolerance_type',
               'fulfillment_tolerance_value', 'settlement_tolerance_value', 'is_active']


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_contract_terms',
        conflict_cols=['name'], update_cols=UPDATE_COLS,
        mode='update_insert', require_non_null=['name'],
    )
