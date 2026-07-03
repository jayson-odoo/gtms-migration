"""legal-entity / master_document_content_snippets — transformer + FK resolution.

The sheet's document_template_id holds a template NAME (e.g. 'SALES_CONTRACT');
resolve it to master_document_templates.id. Merge key: (document_template_id, name).
"""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    # id is omitted — the DB id is serial; the merge key is (document_template_id, name).
    df = clean_df(
        df,
        cols=['name', 'printout_description', 'document_template_id', 'is_active'],
        key_cols=['name'],
        bool_cols=['is_active'],
    )
    df = resolve_fk(df, 'document_template_id', 'master_document_templates', 'name')
    return df
