"""linkages / master_contract_types — exporter. Upsert on code."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_contract_types',
        conflict_cols=['code'], update_cols=['name', 'is_system', 'is_active'],
        mode='update_insert', require_non_null=['code', 'name'],
    )
