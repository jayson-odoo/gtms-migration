"""linkages / inventory_location_storage_rates — transformer + FK resolution.

The 'Storage Charges' tab lists a location's weekly (or monthly) cumulative storage rate,
one row per sequence. The 'GTMS Inventory Location' code is given once per location group and
blank on the following rows (fill-down). Per business decision only Belmont (WP7) storage is
left out; every other location (WP1, NP1, WP2, WP3, PIP) is migrated even though the sheet's
'Excluded' flag also marks the container ones. Tax is SST 6%, i.e. the purchase-side master
tax code '68' (as used by the sibling port-charges sheet).
"""
import pandas as pd

from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

# Storage rates NOT migrated (business decision) — Belmont container location only.
EXCLUDE_LOCATIONS = {'WP7'}


@transformer
def transform(df, *args, **kwargs):
    # fill-down the location code (blank on continuation rows)
    loc = df['GTMS Inventory Location'].astype(str).str.strip().replace('', pd.NA)
    df['GTMS Inventory Location'] = loc.ffill().fillna('')
    df = df[~df['GTMS Inventory Location'].isin(EXCLUDE_LOCATIONS)].copy()

    # SST 6% -> master_taxes purchase code '68'; sheet gives the percentage as e.g. '6%'.
    df['tax_id'] = '68'
    df['tax_code'] = '68'
    df['tax_percentage'] = df['Tax Percentage'].astype(str).str.replace('%', '', regex=False)

    df = df.rename(columns={'GTMS Inventory Location': 'inventory_location_id'})
    df = clean_df(
        df,
        cols=['inventory_location_id', 'sequence', 'duration_unit', 'rate_per_unit',
              'tax_id', 'tax_code', 'tax_percentage'],
        key_cols=['inventory_location_id', 'sequence'],
        int_cols=['sequence'],
        float_cols=['rate_per_unit', 'tax_percentage'],
    )
    df = resolve_fk(df, 'inventory_location_id', 'master_inventory_locations', 'code')
    df = resolve_fk(df, 'tax_id', 'master_taxes', 'code')
    return df
