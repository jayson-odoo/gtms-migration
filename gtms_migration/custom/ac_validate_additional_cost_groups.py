"""additional-charges / master_additional_cost_groups — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='master_additional_cost_groups', keys=['code'],
        check_name='is_additional_cost_group_passed', field_tab='Additional Cost Group Field Level Validator', fk_checks=[])
