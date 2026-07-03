"""linkages / master_price_index_products — transformer + FK resolution.
Junction (price_index_id, product_id). Products not in the Products sheet resolve to NULL
and are skipped at export."""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'code': 'price_index_id', 'product': 'product_id'})
    df = clean_df(df, cols=['price_index_id', 'product_id'], key_cols=['price_index_id', 'product_id'])
    df = resolve_fk(df, 'price_index_id', 'master_price_indexes', 'code')
    # The sheet drops the 'TGQ' product-code prefix (e.g. HMZA -> TGQHMZA); restore it before resolving.
    df['product_id'] = df['product_id'].where(
        df['product_id'].str.startswith('TGQ'), 'TGQ' + df['product_id'])
    df = resolve_fk(df, 'product_id', 'master_products', 'code')
    return df
