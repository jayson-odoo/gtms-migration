"""counterparty-products / master_traders — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = clean_df(df, cols=['id', 'code', 'name'], key_cols=['code'], int_cols=['id'], bool_cols=[], null_cols=[], float_cols=[])
    return df
