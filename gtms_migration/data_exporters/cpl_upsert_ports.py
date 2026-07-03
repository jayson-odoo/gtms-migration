"""counterparty-location / master_ports — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_ports', conflict_cols=['code'], update_cols=['name', 'short_name', 'country', 'state_id', 'region_id', 'reference_1', 'reference_2'],
        mode='on_conflict', fk_filters=[('country', 'master_countries', 'code')], require_non_null=[],
    )
