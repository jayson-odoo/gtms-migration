"""counterparty-location / master_inventory_locations — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='master_inventory_locations', keys=['code', 'legal_entity_id'],
        check_name='is_inventory_locations_passed', field_tab='Inventory Locations Field Level Validator', fk_checks=[])
