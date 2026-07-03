"""counterparty-location / master_ports — transformer."""
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'state': 'state_id', 'region': 'region_id'})
    df = clean_df(df, cols=['code', 'name', 'short_name', 'country', 'state_id', 'region_id', 'reference_1', 'reference_2'], key_cols=['code'], int_cols=[], bool_cols=[], null_cols=['short_name', 'reference_1', 'reference_2'], float_cols=[])
    df = resolve_fk(df, 'state_id', 'master_states', 'name')
    df = resolve_fk(df, 'region_id', 'master_regions', 'name')
    return df
