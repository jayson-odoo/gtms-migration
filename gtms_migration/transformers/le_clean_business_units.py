"""legal-entity / master_business_units — transformer. Merge key: id (DB Merger #7). country is a FK."""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    return clean_df(
        df,
        cols=['id', 'name', 'country'],
        key_cols=['name'],
        int_cols=['id'],
    )
