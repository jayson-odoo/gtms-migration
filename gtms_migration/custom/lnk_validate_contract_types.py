"""linkages / master_contract_types — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_contract_types', keys=['code'],
        check_name='is_contract_type_passed', field_tab='Contract Type Field Level Validator',
    )
