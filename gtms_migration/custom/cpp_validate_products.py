"""counterparty-products / master_products — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_products',
        keys=['code'],
        check_name='is_product_passed',
        field_tab='Products Field Level Validator',
        fk_checks=[],
    )
