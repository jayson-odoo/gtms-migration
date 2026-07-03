"""legal-entity / addresses — transformer.

DB id is serial (the sheet has no id). country is a FK to master_countries(code),
filtered at export. Business key for the merge: address, city, postcode, state.
"""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    return clean_df(
        df,
        cols=['address', 'city', 'postcode', 'state', 'country'],
        key_cols=['address', 'city', 'postcode', 'state'],
    )
