"""counterparty-products / master_products — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_products',
        conflict_cols=['code'],
        update_cols=['contract_number_reference', 'description', 'packing_unit_id', 'default_uom_id', 'hs_code', 'is_active', 'weight', 'standard_cost', 'category'],
        mode='on_conflict',
        fk_filters=[],
        require_non_null=[],
    )
