"""counterparty-products / master_lot_to_uom_conversions — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_lot_to_uom_conversions',
        conflict_cols=['product_id', 'uom_id'],
        update_cols=['multiplier'],
        mode='update_insert',
        fk_filters=[],
        require_non_null=['product_id', 'uom_id'],
    )
