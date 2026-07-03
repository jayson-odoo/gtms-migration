"""counterparty-products / master_specification_details — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'SpecGroupName2': 'specification_group_id', 'SpecName': 'specification_id'})
    df = clean_df(df, cols=['specification_group_id', 'specification_id', 'minimum', 'maximum', 'minimum_basis', 'maximum_basis', 'is_derived'], key_cols=['specification_group_id', 'specification_id'], int_cols=[], bool_cols=['is_derived'], null_cols=['minimum_basis', 'maximum_basis'], float_cols=['minimum', 'maximum'])
    df = resolve_fk(df, 'specification_group_id', 'master_specification_groups', 'name')
    df = resolve_fk(df, 'specification_id', 'master_specifications', 'name')
    return df
