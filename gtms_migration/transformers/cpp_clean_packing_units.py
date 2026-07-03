"""counterparty-products / master_packing_units — transformer.

Adds the container fields. weight_per_container_uom and size_uom are FK to master_uoms.code
(they store the UoM code directly, not an id), so any code not present in master_uoms is
nulled here (and reported) to avoid an FK violation.
"""
import pandas as pd

from gtms_migration.utils.blocks import clean_df
from gtms_migration.utils.pg import read_sql

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={
        'Weight per Container': 'weight_per_container',
        'Weight UoM': 'weight_per_container_uom',
        'Size': 'size',
        'Size UoM': 'size_uom',
    })
    df = clean_df(
        df,
        cols=['code', 'description', 'is_container', 'weight_per_container',
              'weight_per_container_uom', 'size', 'size_uom'],
        key_cols=['code'],
        bool_cols=['is_container'],
        float_cols=['weight_per_container', 'size'],
        null_cols=['description', 'weight_per_container_uom', 'size_uom'],
    )
    valid = set(read_sql('select code from master_uoms')['code'].astype(str).str.strip())
    for col in ['weight_per_container_uom', 'size_uom']:
        bad = df[col].notna() & ~df[col].isin(valid)
        if bad.any():
            print(f'[packing_units] {col}: nulling {int(bad.sum())} code(s) not in master_uoms: '
                  f'{sorted(df.loc[bad, col].unique())} (add them to the UoM sheet)')
            df.loc[bad, col] = pd.NA
    return df
