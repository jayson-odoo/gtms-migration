"""legal-entity / master_payment_terms — transformer.

The sheet 'id' is a code (e.g. '120D'), NOT the bigint DB id, so it is dropped;
the DB id is serial-assigned. Merge key: name. due_date_days is numeric.
"""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    return clean_df(
        df,
        cols=['name', 'contract_description', 'invoice_description',
              'due_date_days', 'payment_mode', 'lc_type'],
        key_cols=['name'],
        int_cols=['due_date_days'],
    )
