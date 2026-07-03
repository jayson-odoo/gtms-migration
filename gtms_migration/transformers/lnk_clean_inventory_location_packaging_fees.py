"""linkages / inventory_location_packaging_fees — transformer + FK resolution.

The 'GTMS Inventory Location' code is listed once per location group and blank for the
following rows (fill-down). The table has no tax columns, so the sheet's tax / before-tax
fee are ignored (packaging_fee is the final fee). Rows with no GTMS code (e.g. Belmont,
which has none) resolve to NULL and are skipped at export.
"""
import pandas as pd

from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    g = df['GTMS Inventory Location'].astype(str).str.strip().replace('', pd.NA)
    df['GTMS Inventory Location'] = g.ffill().fillna('')   # fill-down the location code
    df = df.rename(columns={'GTMS Inventory Location': 'inventory_location_id',
                            'packaging product': 'packaging_product_id'})
    df = clean_df(
        df,
        cols=['inventory_location_id', 'packaging_product_id', 'lower_bound', 'upper_bound', 'packaging_fee'],
        key_cols=['inventory_location_id', 'packaging_product_id'],
        float_cols=['lower_bound', 'upper_bound', 'packaging_fee'],
    )
    df = resolve_fk(df, 'inventory_location_id', 'master_inventory_locations', 'code')
    df = resolve_fk(df, 'packaging_product_id', 'master_products', 'code')
    return df
