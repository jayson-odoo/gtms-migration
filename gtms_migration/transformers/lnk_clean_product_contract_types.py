"""linkages / product_contract_types — transformer + FK resolution."""
from gtms_migration.utils.blocks import clean_df, resolve_fk  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'product': 'product_id'})
    df = clean_df(df, cols=['product_id', 'contract_type_id'], key_cols=['product_id', 'contract_type_id'], int_cols=['contract_type_id'], bool_cols=[], null_cols=[], float_cols=[])
    df = resolve_fk(df, 'product_id', 'master_products', 'code')
    return df
