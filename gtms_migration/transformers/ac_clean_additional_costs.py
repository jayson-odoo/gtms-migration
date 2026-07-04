"""additional-charges / master_additional_costs — transformer + FK resolution.

profit_centers is a JSON column storing an array of profit-center ids; a profit
center is a master_counterparties row. The sheet has the profit-center NAME, so we
resolve it to the counterparty id and JSON-wrap as ["<id>"]. contract_types is already
a JSON array string in the sheet ('["1"]').
"""
import json
import re

import pandas as pd
from gtms_migration.utils.blocks import clean_df, resolve_fk, read_sql

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

COLS = ['name', 'description', 'additional_cost_group_id', 'value_type', 'default_value',
        'account_id', 'transaction_type', 'profit_centers', 'contract_types', 'charges_type', 'is_active']
NULL = ['description', 'account_id', 'transaction_type', 'charges_type', 'contract_types', 'value_type']


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'additional cost group': 'additional_cost_group_id'})
    df = clean_df(df, cols=COLS, key_cols=['name'], bool_cols=['is_active'],
                  null_cols=NULL, float_cols=['default_value'])
    # name/description are varchar(128) in master_additional_costs (the GTMS app enforces
    # the same limit). The sheet has a 132-char outlier; cap to the column limit so the
    # batch doesn't abort with StringDataRightTruncation, and log anything trimmed.
    for col in ['name', 'description']:
        too_long = df[col].notna() & (df[col].astype(str).str.len() > 128)
        for v in df.loc[too_long, col]:
            print(f'[master_additional_costs] truncating {col} to 128 chars: {v!r}')
        df.loc[too_long, col] = df.loc[too_long, col].astype(str).str.slice(0, 128)
    df = resolve_fk(df, 'additional_cost_group_id', 'master_additional_cost_groups', 'name')
    # profit_centers: one OR many names (pipe/semicolon-delimited) -> JSON array of counterparty ids.
    # Scoped to profit centers (code IS NOT NULL) so 'QL INTERNATIONAL PTE. LTD.' can't collide with a cpl row.
    pc = read_sql('select id, name from master_counterparties where code is not null')
    pcmap = {str(n).strip(): int(i) for n, i in zip(pc['name'], pc['id'])}

    def _resolve_pcs(cell):
        if pd.isna(cell) or not str(cell).strip():
            return None
        ids = [str(pcmap[n.strip()]) for n in re.split(r'[|;]', str(cell)) if n.strip() in pcmap]
        return json.dumps(ids) if ids else None

    df['profit_centers'] = df['profit_centers'].map(_resolve_pcs)
    return df
