"""counterparty-products / master_specification_details — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_specification_details', keys=['specification_group_id', 'specification_id'],
        check_name='is_spec_group_spec_passed', field_tab='Spec Group Spec Field Level Validator', fk_checks=[],
    )
