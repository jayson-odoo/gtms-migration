"""counterparty-products / master_packing_units — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_packing_units',
        keys=['code'],
        check_name='is_packing_unit_passed',
        field_tab='Packing Unit Field Level Validator',
        fk_checks=[],
    )
