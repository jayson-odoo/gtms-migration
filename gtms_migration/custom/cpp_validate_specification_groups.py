"""counterparty-products / master_specification_groups — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_specification_groups',
        keys=['name'],
        check_name='is_spec_group_passed',
        field_tab='SpecGroup Field Level Validator',
        fk_checks=[],
    )
