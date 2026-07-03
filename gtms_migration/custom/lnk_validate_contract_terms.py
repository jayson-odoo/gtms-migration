"""linkages / master_contract_terms — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_contract_terms', keys=['name'],
        check_name='is_contract_term_passed',
        field_tab='Contract Terms Field Level Validator',
    )
