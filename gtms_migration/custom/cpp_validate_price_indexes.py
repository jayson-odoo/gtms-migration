"""counterparty-products / master_price_indexes — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_price_indexes', keys=['code'],
        check_name='is_price_index_passed', field_tab='Price Index Field Level Validator', fk_checks=[],
    )
