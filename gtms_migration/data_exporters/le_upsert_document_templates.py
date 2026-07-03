"""legal-entity / master_document_templates — exporter. DB Merger (#43).
match=name (unique index) -> on_conflict. contract_type/document_type FK-filtered.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_document_templates',
        conflict_cols=['name'],
        update_cols=['contract_type', 'printout_view_name', 'document_type',
                     'transaction_type', 'printout_format'],
        mode='on_conflict',
        fk_filters=[('contract_type', 'master_contract_types', 'code'),
                    ('document_type', 'master_document_types', 'code')],
    )
