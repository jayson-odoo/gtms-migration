"""counterparty-products / master_uoms — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_uoms',
        conflict_cols=['code'],
        update_cols=['description'],
        mode='on_conflict',
        fk_filters=[],
        require_non_null=[],
    )
