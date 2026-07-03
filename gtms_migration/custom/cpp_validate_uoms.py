"""counterparty-products / master_uoms — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_uoms',
        keys=['code'],
        check_name='is_uom_passed',
        field_tab='UoM Field Level Validator',
        fk_checks=[],
    )
