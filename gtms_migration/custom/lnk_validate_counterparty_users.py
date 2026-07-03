"""linkages / counterparty_users — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='counterparty_users', keys=['counterparty_id', 'user_id'],
        check_name='is_counterparty_user_passed',
        field_tab='User x Profit Center Field Level Validator',
    )
