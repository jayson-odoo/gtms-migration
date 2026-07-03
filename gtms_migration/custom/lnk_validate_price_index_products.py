"""linkages / master_price_index_products — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_price_index_products', keys=['price_index_id', 'product_id'],
        check_name='is_price_index_product_passed',
        field_tab='Price Index Product Field Level Validator',
    )
