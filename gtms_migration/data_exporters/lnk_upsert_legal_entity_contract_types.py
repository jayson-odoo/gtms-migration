"""linkages / legal_entity_contract_types — exporter (junction)."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'legal_entity_contract_types',
        conflict_cols=['legal_entity_id', 'contract_type_id'], update_cols=[],
        mode='on_conflict', require_non_null=['legal_entity_id', 'contract_type_id'],
    )
