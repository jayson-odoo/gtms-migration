"""linkages / legal_entity_taxes — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(sheet_df=df, db_table='legal_entity_taxes', keys=['legal_entity_id', 'tax_id'],
        check_name='is_legal_entity_tax_passed', field_tab='Legal Entity x Tax Field Level Validator', fk_checks=[])
