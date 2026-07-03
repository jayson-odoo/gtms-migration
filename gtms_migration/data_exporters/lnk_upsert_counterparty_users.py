"""linkages / counterparty_users — exporter (junction)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'counterparty_users',
        conflict_cols=['counterparty_id', 'user_id'], update_cols=[],
        mode='on_conflict', require_non_null=['counterparty_id', 'user_id'],
    )
