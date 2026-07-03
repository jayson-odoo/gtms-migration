"""counterparty-products / master_lot_to_uom_conversions — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'code': 'product_id', 'UoM': 'uom_id'})
    df = clean_df(df, cols=['product_id', 'uom_id', 'multiplier'], key_cols=['product_id', 'uom_id'], int_cols=[], bool_cols=[], null_cols=[], float_cols=['multiplier'])
    df = resolve_fk(df, 'product_id', 'master_products', 'code')
    df = resolve_fk(df, 'uom_id', 'master_uoms', 'code')
    return df
