"""linkages / master_price_build_up_components — exporter. Upsert on code (code_unique)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_price_build_up_components',
        conflict_cols=['code'], update_cols=['name', 'is_active'], mode='on_conflict',
    )
