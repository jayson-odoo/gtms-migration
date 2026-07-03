"""legal-entity / master_document_content_snippets — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_document_content_snippets',
        keys=['document_template_id', 'name'],
        check_name='is_document_content_snippet_passed',
        field_tab='Document Content Snippet Field Level Validator',
    )
