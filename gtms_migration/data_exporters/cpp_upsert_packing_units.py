"""counterparty-products / master_packing_units — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_packing_units',
        conflict_cols=['code'],
        update_cols=['description', 'is_container', 'weight_per_container',
                     'weight_per_container_uom', 'size', 'size_uom'],
        mode='on_conflict',
        fk_filters=[],
        require_non_null=[],
    )
