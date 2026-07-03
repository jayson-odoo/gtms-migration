"""linkages / master_price_build_up_components — transformer. Standalone master, key = code."""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    return clean_df(df, cols=['code', 'name', 'is_active'], key_cols=['code'], bool_cols=['is_active'])
