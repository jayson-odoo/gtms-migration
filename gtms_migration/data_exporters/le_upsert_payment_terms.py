"""legal-entity / master_payment_terms — exporter. DB Merger (#54).
match=name (no unique index) -> update_insert. No FKs.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_payment_terms',
        conflict_cols=['name'],
        update_cols=['contract_description', 'invoice_description',
                     'due_date_days', 'payment_mode', 'lc_type'],
        mode='update_insert',
    )
