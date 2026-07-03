"""linkages / counterparty_products — exporter (junction; ON CONFLICT keeps the row, backfills ts)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'counterparty_products', conflict_cols=['counterparty_id', 'product_id'], update_cols=[],
        mode='on_conflict', fk_filters=[], require_non_null=['counterparty_id', 'product_id'],
    )
