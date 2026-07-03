"""linkages / master_integration_references — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_integration_references',
        # merged vendor+customer counterparties produce 2+ rows sharing integratable_id, so the
        # reference columns are part of a row's identity; include them so the key is unique and the
        # sheet<->db join doesn't mis-pair rows (which produced spurious field mismatches).
        keys=['external_system_id', 'integratable_type', 'integratable_id',
              'vendor_reference_no', 'customer_reference_no'],
        check_name='is_integration_reference_passed',
        field_tab='Integration Reference Field Level Validator',
    )
