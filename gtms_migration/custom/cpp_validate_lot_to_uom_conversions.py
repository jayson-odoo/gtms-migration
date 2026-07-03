"""counterparty-products / master_lot_to_uom_conversions — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_lot_to_uom_conversions', keys=['product_id', 'uom_id'],
        check_name='is_product_lot_to_uom_passed', field_tab='Product Lot to UoM Conversion Field Level Validator', fk_checks=[],
    )
