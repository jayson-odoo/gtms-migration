"""linkages / contract_term_incoterms — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='contract_term_incoterms', keys=['contract_term_id', 'incoterm_id'],
        check_name='is_contract_term_incoterm_passed',
        field_tab='Contract Term x Incoterm Field Level Validator',
    )
