"""linkages / model_has_roles — transformer + FK resolution (polymorphic junction).
user_name -> model_id (users.id by name), role_name -> role_id (roles.id by name);
model_type ('App\\Models\\User') comes straight from the sheet."""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'user_name': 'model_id', 'role_name': 'role_id'})
    df = clean_df(df, cols=['role_id', 'model_id', 'model_type'],
                  key_cols=['role_id', 'model_id', 'model_type'])
    df = resolve_fk(df, 'role_id', 'roles', 'name')
    df = resolve_fk(df, 'model_id', 'users', 'name')
    return df
