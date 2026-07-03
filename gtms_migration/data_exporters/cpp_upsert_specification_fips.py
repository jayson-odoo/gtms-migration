"""counterparty-products / master_specification_fips — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_specification_fips',
        conflict_cols=['specification_detail_id', 'fip'],
        update_cols=['minimum', 'maximum'],
        mode='update_insert',
        fk_filters=[],
        require_non_null=['specification_detail_id'],
    )
