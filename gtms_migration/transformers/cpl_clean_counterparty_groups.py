"""counterparty-location / master_counterparty_groups — transformer."""
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = clean_df(df, cols=['name', 'is_active'], key_cols=['name'], int_cols=[], bool_cols=['is_active'], null_cols=[], float_cols=[])
    return df
