"""counterparty-location / master_inventory_locations — transformer."""
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'port_code': 'port_id'})
    df = clean_df(df, cols=['code', 'name', 'short_name', 'legal_entity_id', 'port_id', 'country', 'currency', 'location_type'], key_cols=['code'], int_cols=[], bool_cols=[], null_cols=['short_name', 'currency'], float_cols=[])
    df = resolve_fk(df, 'legal_entity_id', 'master_legal_entities', 'name')
    df = resolve_fk(df, 'port_id', 'master_ports', 'code')
    return df
