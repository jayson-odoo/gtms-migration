"""acl / role_has_permissions — transformer + FK resolution.

The sheet's numeric permission_id/role_id are source-system ids that do NOT match the
destination, so they are ignored. Instead we resolve the destination ids by NAME:
permission_name -> permissions.id, role_name -> roles.id (both guard 'web', name-unique).
Output is the pure junction (permission_id, role_id) of destination ids.
"""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = clean_df(df, cols=['permission_name', 'role_name'],
                  key_cols=['permission_name', 'role_name'])
    df['permission_id'] = df['permission_name']
    df = resolve_fk(df, 'permission_id', 'permissions', 'name')
    df['role_id'] = df['role_name']
    df = resolve_fk(df, 'role_id', 'roles', 'name')
    return df[['permission_id', 'role_id']]
