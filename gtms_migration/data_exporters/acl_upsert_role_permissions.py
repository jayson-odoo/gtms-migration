"""acl / role_has_permissions — exporter (junction).

role_has_permissions is a pure junction: PK (permission_id, role_id), no other columns
and no timestamps -> timestamp_cols=(), update_cols=[] => ON CONFLICT DO NOTHING.
The sheet has many duplicate (permission, role) pairs; export_table collapses them.
Rows whose name didn't resolve to an id (NULL) are skipped via require_non_null.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'role_has_permissions',
        conflict_cols=['permission_id', 'role_id'], update_cols=[],
        mode='on_conflict',
        require_non_null=['permission_id', 'role_id'],
        timestamp_cols=(),
    )
