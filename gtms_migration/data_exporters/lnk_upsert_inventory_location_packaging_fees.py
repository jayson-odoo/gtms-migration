"""linkages / inventory_location_packaging_fees — exporter. No unique index on the business
key, so update_insert keyed on (inventory_location_id, packaging_product_id)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'inventory_location_packaging_fees',
        # Tiered fees: the same (location, product) has multiple bound ranges, so the bounds
        # are part of the business key (else tiers collapse onto one row).
        conflict_cols=['inventory_location_id', 'packaging_product_id', 'lower_bound', 'upper_bound'],
        update_cols=['packaging_fee'],
        mode='update_insert',
        require_non_null=['inventory_location_id', 'packaging_product_id',
                          'lower_bound', 'upper_bound', 'packaging_fee'],
    )
