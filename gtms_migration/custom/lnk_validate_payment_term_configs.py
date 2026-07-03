"""linkages / payment_term_configs — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='payment_term_configs', keys=['payment_term_id', 'document_type'],
        check_name='is_payment_term_config_passed',
        field_tab='Payment Term Configs Field Level Validator',
    )
