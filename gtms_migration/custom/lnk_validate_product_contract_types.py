"""linkages / product_contract_types — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='product_contract_types', keys=['product_id', 'contract_type_id'],
        check_name='is_product_contract_type_passed', field_tab='Product x Contract Type Field Level Validator', fk_checks=[])
