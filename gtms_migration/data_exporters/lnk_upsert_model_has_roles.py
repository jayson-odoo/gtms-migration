"""linkages / model_has_roles — exporter. Polymorphic junction with no timestamp columns;
PK = (role_id, model_id, model_type) -> ON CONFLICT DO NOTHING (timestamp_cols=())."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'model_has_roles',
        conflict_cols=['role_id', 'model_id', 'model_type'], update_cols=[],
        mode='on_conflict', timestamp_cols=(),
        require_non_null=['role_id', 'model_id', 'model_type'],
    )
