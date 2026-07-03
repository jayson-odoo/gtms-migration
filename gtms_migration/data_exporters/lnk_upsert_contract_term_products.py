"""linkages / contract_term_products — exporter (junction)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'contract_term_products',
        conflict_cols=['contract_term_id', 'product_id'], update_cols=[],
        mode='on_conflict', require_non_null=['contract_term_id', 'product_id'],
    )
