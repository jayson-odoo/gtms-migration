"""legal-entity / master_payment_terms — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_payment_terms',
        keys=['name'],
        check_name='is_payment_terms_passed',
        field_tab='Payment Term Field Level Validator',
    )
