"""counterparty-products / master_specification_fips — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'SpecGroupName': 'specification_group_id', 'SpecName': 'specification_id'})
    df = clean_df(df, cols=['specification_group_id', 'specification_id', 'minimum', 'maximum', 'fip'], key_cols=['specification_group_id', 'specification_id'], int_cols=['fip'], bool_cols=[], null_cols=[], float_cols=['minimum', 'maximum'])
    df = resolve_fk(df, 'specification_group_id', 'master_specification_groups', 'name')
    df = resolve_fk(df, 'specification_id', 'master_specifications', 'name')
    df = resolve_fk_composite(df, 'specification_detail_id', 'master_specification_details', ['specification_group_id', 'specification_id'], ['specification_group_id', 'specification_id'])
    df = df.drop(columns=['specification_group_id', 'specification_id'])
    return df
