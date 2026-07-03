"""counterparty-location / master_inventory_locations — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_inventory_locations', conflict_cols=['code', 'legal_entity_id'], update_cols=['name', 'short_name', 'port_id', 'country', 'currency', 'location_type'],
        mode='on_conflict', fk_filters=[('country', 'master_countries', 'code')], require_non_null=['legal_entity_id'],
    )
