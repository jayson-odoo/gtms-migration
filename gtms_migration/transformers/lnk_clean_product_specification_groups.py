"""linkages / product_specification_groups — transformer + FK resolution."""
from gtms_migration.utils.blocks import clean_df, resolve_fk  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'spec_group': 'specification_group_id', 'code': 'product_id'})
    df = clean_df(df, cols=['product_id', 'specification_group_id'], key_cols=['product_id', 'specification_group_id'], int_cols=[], bool_cols=[], null_cols=[], float_cols=[])
    df = resolve_fk(df, 'product_id', 'master_products', 'code')
    df = resolve_fk(df, 'specification_group_id', 'master_specification_groups', 'name')
    return df
