"""legal-entity / master_regions — transformer (clean + type-cast).

Keep only the target columns, coerce types, and drop blank rows. Output columns
match the master_regions insert set: id, name, is_active. (The exporter drops `id`
before insert so the sequence assigns it; rows match existing DB rows by name.)
"""
import pandas as pd

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

TRUE_SET = {'true', 't', '1', 'yes', 'y'}


@transformer
def transform(df, *args, **kwargs):
    df = df[['id', 'name', 'is_active']].copy()

    # Drop rows with no business key (trailing blank sheet rows).
    df['name'] = df['name'].astype(str).str.strip()
    df = df[df['name'] != ''].copy()

    df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')
    df['is_active'] = df['is_active'].astype(str).str.strip().str.lower().isin(TRUE_SET)

    return df.reset_index(drop=True)


@test
def test_output(df) -> None:
    assert not df.empty, 'No regions after cleaning'
    assert df['name'].is_unique, 'Duplicate region name(s) — would break ON CONFLICT (name)'
    assert df['is_active'].dtype == bool, 'is_active not boolean'
