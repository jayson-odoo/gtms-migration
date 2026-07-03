"""linkages / user_contract_types — transformer + FK resolution (junction).
Sheet columns already named user_id / contract_type_id but hold NAMES — resolve to ids."""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = clean_df(df, cols=['user_id', 'contract_type_id'],
                  key_cols=['user_id', 'contract_type_id'])
    df = resolve_fk(df, 'user_id', 'users', 'name')
    df = resolve_fk(df, 'contract_type_id', 'master_contract_types', 'name')
    return df
