"""counterparty-products / master_specification_fips — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_specification_fips', keys=['specification_detail_id', 'fip'],
        check_name='is_spec_group_fip_passed', field_tab='SpecGroupFIP Field Level Validator', fk_checks=[],
    )
