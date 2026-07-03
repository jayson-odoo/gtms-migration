"""counterparty-location / master_ports — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='master_ports', keys=['code'],
        check_name='is_ports_passed', field_tab='Ports Field Level Validator', fk_checks=[{'col': 'country', 'ref_table': 'master_countries', 'ref_col': 'code'}])
