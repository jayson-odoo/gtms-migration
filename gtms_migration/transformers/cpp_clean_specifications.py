"""counterparty-products / master_specifications — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = clean_df(df, cols=['name', 'description', 'value_unit', 'value_type'], key_cols=['name'], int_cols=[], bool_cols=[], null_cols=['description', 'value_unit', 'value_type'], float_cols=[])
    return df
