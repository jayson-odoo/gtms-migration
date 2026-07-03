"""acl / users — transformer.

The sheet's 'password' column actually holds the user's email, so it is renamed to
`email` (the DB's NOT NULL/unique identity column and our upsert business key). The DB
`password` column is set later, on insert only (see the exporter). The three timestamp
columns (password_expired_at, valid_from, valid_to) are parsed to datetimes; blanks -> NULL.
"""
import pandas as pd

from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

DATE_COLS = ['password_expired_at', 'valid_from', 'valid_to']


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'password': 'email'})
    df = clean_df(
        df,
        cols=['name', 'email', 'timezone', 'is_active'] + DATE_COLS + ['code'],
        key_cols=['email'],
        bool_cols=['is_active'],
        null_cols=['code'],
    )
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c].replace('', pd.NA), errors='coerce')
    return df


@test
def test_output(df) -> None:
    assert not df.empty, 'No users after cleaning'
    assert df['email'].is_unique, 'Duplicate emails in sheet (email is the unique key)'
    assert df['is_active'].dtype == bool, 'is_active not boolean'
