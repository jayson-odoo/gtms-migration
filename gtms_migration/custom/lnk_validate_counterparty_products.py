"""linkages / counterparty_products — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='counterparty_products', keys=['counterparty_id', 'product_id'],
        check_name='is_counterparty_product_passed', field_tab='Profit Center x Product Field Level Validator', fk_checks=[])
