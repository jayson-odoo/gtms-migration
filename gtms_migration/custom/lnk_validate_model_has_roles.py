"""linkages / model_has_roles — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='model_has_roles', keys=['role_id', 'model_id', 'model_type'],
        check_name='is_user_role_passed', field_tab='User Roles Field Level Validator',
    )
