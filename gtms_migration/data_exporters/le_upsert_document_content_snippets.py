"""legal-entity / master_document_content_snippets — exporter. DB Merger (#50).
match=(document_template_id, name) (unique index) -> on_conflict. document_template_id NOT NULL.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_document_content_snippets',
        conflict_cols=['document_template_id', 'name'],
        update_cols=['printout_description', 'is_active'],
        mode='on_conflict',
        require_non_null=['document_template_id'],
    )
