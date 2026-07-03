"""counterparty-products / master_price_indexes — transformer + FK resolution."""
import pandas as pd  # noqa: F401
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'source_id_code': 'source_id', 'uom': 'uom_id'})
    df = clean_df(df, cols=['code', 'description', 'month', 'contract_type_id', 'application', 'source_id', 'is_integration', 'ticker_code', 'currency', 'incoterm_id', 'uom_id', 'basis_port_id', 'forward_months', 'is_active'], key_cols=['code'], int_cols=['contract_type_id', 'incoterm_id', 'forward_months'], bool_cols=['is_integration', 'is_active'], null_cols=['description', 'ticker_code', 'application', 'month', 'currency', 'basis_port_id'], float_cols=[])
    df = resolve_fk(df, 'source_id', 'master_external_systems', 'code')
    df = resolve_fk(df, 'uom_id', 'master_uoms', 'code')
    # basis_port_id arrives as a port CODE (e.g. 'MYPKG'); resolve to master_ports.id.
    df = resolve_fk(df, 'basis_port_id', 'master_ports', 'code')
    return df
