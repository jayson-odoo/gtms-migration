"""counterparty-products / master_specification_details — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_specification_details',
        conflict_cols=['specification_group_id', 'specification_id'],
        update_cols=['minimum', 'maximum', 'minimum_basis', 'maximum_basis', 'is_derived'],
        mode='update_insert',
        fk_filters=[],
        require_non_null=['specification_group_id', 'specification_id'],
    )
