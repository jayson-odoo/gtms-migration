"""counterparty-location / master_counterparty_groups — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='master_counterparty_groups', keys=['name'],
        check_name='is_counterparty_group_passed', field_tab='Counterparty Group Field Level Validator', fk_checks=[])
