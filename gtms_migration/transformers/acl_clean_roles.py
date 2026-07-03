"""acl / roles — transformer (clean). Business key = (name, guard_name)."""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    return clean_df(df, cols=['name', 'guard_name'], key_cols=['name', 'guard_name'])
