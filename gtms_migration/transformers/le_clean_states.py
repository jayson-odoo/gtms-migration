"""legal-entity / master_states — transformer (clean + type-cast).

The DB column `country` stores the country *code* (e.g. 'MY') directly — no FK id
lookup. The sheet's helper columns (exist_in_countries, concat) are dropped; they
were KNIME validation scaffolding. Output: id, name, country, is_active.
"""
import pandas as pd

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

TRUE_SET = {'true', 't', '1', 'yes', 'y'}


@transformer
def transform(df, *args, **kwargs):
    df = df[['id', 'name', 'country', 'is_active']].copy()

    df['name'] = df['name'].astype(str).str.strip()
    df['country'] = df['country'].astype(str).str.strip()
    # Drop trailing blank sheet rows (no business key).
    df = df[(df['name'] != '') & (df['country'] != '')].copy()

    df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')
    df['is_active'] = df['is_active'].astype(str).str.strip().str.lower().isin(TRUE_SET)

    # The source sheet contains some duplicate (name, country) rows. KNIME's DB Merger
    # collapses them by key, and our update_insert upsert handles repeated keys safely,
    # so we keep them (last write wins) and just report the count.
    dups = int(df.duplicated(subset=['name', 'country']).sum())
    if dups:
        print(f'[le_clean_states] note: {dups} duplicate (name, country) row(s) in source sheet')

    return df.reset_index(drop=True)


@test
def test_output(df) -> None:
    assert not df.empty, 'No states after cleaning'
    assert df['id'].notna().all(), 'Null id after numeric coercion'
    assert df['is_active'].dtype == bool, 'is_active not boolean'
