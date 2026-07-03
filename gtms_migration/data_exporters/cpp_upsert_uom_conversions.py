"""counterparty-products / master_uom_conversions — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_uom_conversions',
        conflict_cols=['product_id', 'from_uom_id', 'to_uom_id'],
        update_cols=['multiplier'],
        mode='update_insert',
        fk_filters=[],
        # multiplier is NOT NULL in the DB; rows with a blank multiplier (e.g. PMQHBAG
        # placeholder rows, or is_derived rows with no value) are skipped + reported here
        # instead of aborting the whole batch.
        require_non_null=['product_id', 'from_uom_id', 'to_uom_id', 'multiplier'],
    )
