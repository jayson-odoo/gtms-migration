"""linkages / counterparty_products — transformer + FK resolution."""
from gtms_migration.utils.blocks import clean_df, resolve_fk  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'name': 'counterparty_id', 'product': 'product_id'})
    df = clean_df(df, cols=['counterparty_id', 'product_id'], key_cols=['counterparty_id', 'product_id'], int_cols=[], bool_cols=[], null_cols=[], float_cols=[])
    # The 'Profit Center x Product' sheet links PROFIT CENTERS to products. The same names
    # also exist as (codeless) counterparties, so scope the name->id lookup to profit centers
    # (code IS NOT NULL) — this maps QL FEED->id1 / QL INTERNATIONAL->id2 unambiguously.
    df = resolve_fk(df, 'counterparty_id', 'master_counterparties', 'name', where='code IS NOT NULL')
    df = resolve_fk(df, 'product_id', 'master_products', 'code')
    return df
