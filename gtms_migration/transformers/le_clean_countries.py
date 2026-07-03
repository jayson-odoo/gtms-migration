"""legal-entity / master_countries — transformer (clean + type-cast).

Mirrors the KNIME String-to-Number / Rule-Engine steps for the Countries branch:
keep only the target columns, coerce types, and drop blank rows. Output columns
match the master_countries insert set: id, code, name, is_active.
"""
import pandas as pd

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

TRUE_SET = {'true', 't', '1', 'yes', 'y'}


@transformer
def transform(df, *args, **kwargs):
    df = df[['id', 'code', 'name', 'is_active']].copy()

    # Drop rows with no business key (trailing blank sheet rows).
    df['code'] = df['code'].astype(str).str.strip()
    df = df[df['code'] != ''].copy()

    df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')
    df['name'] = df['name'].astype(str).str.strip()
    df['is_active'] = df['is_active'].astype(str).str.strip().str.lower().isin(TRUE_SET)

    return df.reset_index(drop=True)


@test
def test_output(df) -> None:
    assert not df.empty, 'No countries after cleaning'
    assert df['code'].is_unique, 'Duplicate country code(s) — would break ON CONFLICT (code)'
    assert df['id'].notna().all(), 'Null id after numeric coercion'
    assert df['is_active'].dtype == bool, 'is_active not boolean'
