"""acl / roles — exporter. Upsert on (name, guard_name) (roles_name_guard_name_unique).
roles has only the two business columns plus timestamps, so update_cols is empty —
ON CONFLICT just backfills created_at/updated_at and keeps the row."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'roles', conflict_cols=['name', 'guard_name'], update_cols=[],
        mode='on_conflict',
    )
