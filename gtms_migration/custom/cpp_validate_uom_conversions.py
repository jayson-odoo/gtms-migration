"""counterparty-products / master_uom_conversions — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_uom_conversions', keys=['product_id', 'from_uom_id', 'to_uom_id'],
        check_name='is_product_uom_conversion_passed', field_tab='Product UoM Conversion Field Level Validator', fk_checks=[],
    )
