"""acl / users — validation block (runs after upsert). Keyed on email; `password` is
intentionally absent from the compared df (placeholder != stored hash)."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='users',
        keys=['email'],
        check_name='is_users_passed',
        field_tab='Users Field Level Validator',
    )
