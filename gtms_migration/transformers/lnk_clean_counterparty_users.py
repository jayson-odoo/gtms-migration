"""linkages / counterparty_users — transformer + FK resolution (junction).
Maps users to profit centers: user resolved by email, profit center by code (QLF/QLI)."""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'user': 'user_id', 'profit_center': 'counterparty_id'})
    df = clean_df(df, cols=['user_id', 'counterparty_id'], key_cols=['user_id', 'counterparty_id'])
    df = resolve_fk(df, 'user_id', 'users', 'email')
    df = resolve_fk(df, 'counterparty_id', 'master_counterparties', 'code')
    return df
