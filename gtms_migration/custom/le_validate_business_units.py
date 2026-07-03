"""legal-entity / master_business_units — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_business_units',
        keys=['id'],
        check_name='is_business_units_passed',
        field_tab='Business Units Field Level Validator',
        fk_checks=[{'col': 'country', 'ref_table': 'master_countries', 'ref_col': 'code'}],
    )
