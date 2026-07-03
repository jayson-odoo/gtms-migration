"""linkages / inventory_location_packaging_fees — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='inventory_location_packaging_fees',
        keys=['inventory_location_id', 'packaging_product_id', 'lower_bound', 'upper_bound'],
        check_name='is_inventory_location_packing_charge_passed',
        field_tab='Inventory Location Packing Charges Field Level Validator',
    )
