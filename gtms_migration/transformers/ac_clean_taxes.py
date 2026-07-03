"""additional-charges / master_taxes — transformer."""
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = clean_df(df, cols=['code', 'name', 'short_description', 'contract_description', 'transaction_type', 'percentage', 'applicable_from', 'applicable_to', 'is_active'], key_cols=['code'], int_cols=[], bool_cols=['is_active'], null_cols=['short_description', 'contract_description', 'transaction_type', 'applicable_from', 'applicable_to'], float_cols=['percentage'])
    return df
