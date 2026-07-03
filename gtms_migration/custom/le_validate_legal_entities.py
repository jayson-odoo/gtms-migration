"""legal-entity / master_legal_entities — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_legal_entities',
        keys=['code'],
        check_name='is_legal_entities_passed',
        field_tab='Legal Entity Field Level Validator',
        fk_checks=[{'col': 'country', 'ref_table': 'master_countries', 'ref_col': 'code'},
                   {'col': 'currency', 'ref_table': 'master_currencies', 'ref_col': 'code'}],
    )
