"""legal-entity / master_document_templates — transformer.
contract_type and document_type are FKs (filtered at export). Merge key: name.
"""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    # No 'id' column: the sheet no longer carries it and we never write the sheet id
    # anyway (DB assigns id; merge key is name). Selecting 'id' would KeyError.
    return clean_df(
        df,
        cols=['name', 'contract_type', 'printout_view_name',
              'document_type', 'transaction_type', 'printout_format'],
        key_cols=['name'],
    )
