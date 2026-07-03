"""counterparty-products / master_products — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'GTMS Packing Unit': 'packing_unit_id', 'default_uom': 'default_uom_id'})
    df = clean_df(df, cols=['code', 'contract_number_reference', 'description', 'packing_unit_id', 'default_uom_id', 'hs_code', 'is_active', 'weight', 'standard_cost', 'category'], key_cols=['code'], int_cols=[], bool_cols=['is_active'], null_cols=['contract_number_reference', 'description', 'hs_code', 'category'], float_cols=['weight', 'standard_cost'])
    df = resolve_fk(df, 'packing_unit_id', 'master_packing_units', 'code')
    df = resolve_fk(df, 'default_uom_id', 'master_uoms', 'code')
    return df
