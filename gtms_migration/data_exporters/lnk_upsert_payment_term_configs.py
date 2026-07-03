"""linkages / payment_term_configs — exporter. Upsert on (payment_term_id, document_type)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'payment_term_configs',
        conflict_cols=['payment_term_id', 'document_type'],
        update_cols=['percentage', 'billed_basis'],
        mode='on_conflict',
        require_non_null=['payment_term_id', 'percentage', 'billed_basis'],
    )
