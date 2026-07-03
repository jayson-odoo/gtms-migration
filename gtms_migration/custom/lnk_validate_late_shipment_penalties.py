"""linkages / master_late_shipment_penalties — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df, db_table='master_late_shipment_penalties',
        keys=['lower_bound_days', 'upper_bound_days'],
        check_name='is_late_shipment_penalty_passed',
        field_tab='Late Shipment Penalty Field Level Validator',
    )
