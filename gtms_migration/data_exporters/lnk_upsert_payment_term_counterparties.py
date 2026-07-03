"""linkages / payment_term_counterparties — exporter.

The DB unique index is (payment_term_id, counterparty_id, transaction_type), but transaction_type
is always blank here -> NULLs are distinct under a unique index, so ON CONFLICT can't dedup. Use
update_insert keyed on (payment_term_id, counterparty_id) for an idempotent match; transaction_type
(NULL) is still inserted.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'payment_term_counterparties',
        conflict_cols=['payment_term_id', 'counterparty_id'],
        update_cols=[],
        mode='update_insert',
        require_non_null=['payment_term_id', 'counterparty_id'],
    )
