"""linkages / product_specification_groups — exporter (junction; ON CONFLICT keeps the row, backfills ts)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'product_specification_groups', conflict_cols=['product_id', 'specification_group_id'], update_cols=[],
        mode='on_conflict', fk_filters=[], require_non_null=['product_id', 'specification_group_id'],
    )
