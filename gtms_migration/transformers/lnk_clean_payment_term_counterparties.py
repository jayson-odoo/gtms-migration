"""linkages / payment_term_counterparties — transformer + FK resolution.

Links payment terms to PROFIT CENTERS (the sheet's counterparties are all is_internal,
QL FEED / QL INTERNATIONAL), so resolve the counterparty name scoped to profit centers
(code IS NOT NULL) to avoid the codeless-counterparty namesakes. transaction_type is blank.
"""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'name': 'payment_term_id', 'counterparty': 'counterparty_id'})
    df = clean_df(
        df,
        cols=['payment_term_id', 'counterparty_id', 'transaction_type'],
        key_cols=['payment_term_id', 'counterparty_id'],
        null_cols=['transaction_type'],
    )
    df = resolve_fk(df, 'payment_term_id', 'master_payment_terms', 'name')
    df = resolve_fk(df, 'counterparty_id', 'master_counterparties', 'name', where='code IS NOT NULL')
    return df
