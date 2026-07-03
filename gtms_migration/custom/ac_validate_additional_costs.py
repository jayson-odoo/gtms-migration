"""additional-charges / master_additional_costs — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='master_additional_costs', keys=['name'],
        check_name='is_additional_cost_passed', field_tab='Additonal Costs Field Level Validator', fk_checks=[])
