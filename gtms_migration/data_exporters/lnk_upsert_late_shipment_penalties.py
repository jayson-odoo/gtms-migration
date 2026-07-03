"""linkages / master_late_shipment_penalties — exporter. No unique index on the business
key, so update_insert keyed on the day range (lower_bound_days, upper_bound_days)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_late_shipment_penalties',
        conflict_cols=['lower_bound_days', 'upper_bound_days'],
        update_cols=['penalty_percentage', 'is_active'],
        mode='update_insert',
        require_non_null=['lower_bound_days', 'upper_bound_days', 'penalty_percentage'],
    )
