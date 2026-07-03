"""counterparty-products / master_specifications — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_specifications',
        conflict_cols=['name'],
        update_cols=['description', 'value_unit', 'value_type'],
        mode='update_insert',
        fk_filters=[],
        require_non_null=[],
    )
