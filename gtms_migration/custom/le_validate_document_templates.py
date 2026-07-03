"""legal-entity / master_document_templates — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_document_templates',
        keys=['name'],
        check_name='is_document_template_passed',
        field_tab='Document Template Field Level Validator',
        fk_checks=[{'col': 'contract_type', 'ref_table': 'master_contract_types', 'ref_col': 'code'},
                   {'col': 'document_type', 'ref_table': 'master_document_types', 'ref_col': 'code'}],
    )
