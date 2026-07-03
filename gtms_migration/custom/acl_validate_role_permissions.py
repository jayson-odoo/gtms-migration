"""acl / role_has_permissions — validation block (runs after upsert)."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='role_has_permissions',
        keys=['permission_id', 'role_id'],
        check_name='is_role_permission_passed',
        field_tab='Role Permission Field Level Validator',
    )
