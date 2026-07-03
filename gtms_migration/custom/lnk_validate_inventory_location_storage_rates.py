"""linkages / inventory_location_storage_rates — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='inventory_location_storage_rates',
        keys=['inventory_location_id', 'sequence'],
        check_name='is_inventory_location_storage_charge_passed',
        field_tab='Inventory Location Storage Charges Field Level Validator',
    )
