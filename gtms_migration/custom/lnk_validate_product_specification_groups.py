"""linkages / product_specification_groups — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='product_specification_groups', keys=['product_id', 'specification_group_id'],
        check_name='is_spec_group_product_passed', field_tab='Spec Group x Product Field Level Validator', fk_checks=[])
