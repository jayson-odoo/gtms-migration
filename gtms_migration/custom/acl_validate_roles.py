"""acl / roles — validation block (runs after upsert)."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='roles',
        keys=['name', 'guard_name'],
        check_name='is_roles_passed',
        field_tab='Roles Field Level Validator',
    )
