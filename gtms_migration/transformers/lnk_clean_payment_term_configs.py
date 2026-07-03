"""linkages / payment_term_configs — transformer + FK resolution.
Merge key: (payment_term_id, document_type). percentage/billed_basis are NOT NULL."""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'payment_term': 'payment_term_id'})
    df = clean_df(
        df,
        cols=['payment_term_id', 'document_type', 'percentage', 'billed_basis'],
        key_cols=['payment_term_id', 'document_type'],
        float_cols=['percentage'],
        null_cols=['billed_basis'],
    )
    df = resolve_fk(df, 'payment_term_id', 'master_payment_terms', 'name')
    return df
