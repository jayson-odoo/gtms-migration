"""counterparty-location / master_counterparty_groups — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_counterparty_groups', conflict_cols=['name'], update_cols=['is_active'],
        mode='on_conflict', fk_filters=[], require_non_null=[],
    )
