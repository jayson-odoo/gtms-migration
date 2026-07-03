"""linkages / inventory_location_storage_rates — exporter. No unique index on the business
key, so update_insert keyed on (inventory_location_id, sequence)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'inventory_location_storage_rates',
        conflict_cols=['inventory_location_id', 'sequence'],
        update_cols=['duration_unit', 'rate_per_unit', 'tax_id', 'tax_code', 'tax_percentage'],
        mode='update_insert',
        require_non_null=['inventory_location_id', 'sequence', 'duration_unit', 'rate_per_unit'],
    )
