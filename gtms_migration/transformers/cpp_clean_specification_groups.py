"""counterparty-products / master_specification_groups — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.replace(r'^\s*\[NULL\]\s*$', '', regex=True)  # literal [NULL] -> blank
    # Sheet column sales_spec_group_description maps to DB column sales_contract_description.
    df = df.rename(columns={'sales_spec_group_description': 'sales_contract_description'})
    df = clean_df(df, cols=['name', 'description', 'sales_contract_description', 'is_active'],
                  key_cols=['name'], bool_cols=['is_active'],
                  null_cols=['description', 'sales_contract_description'])
    return df
