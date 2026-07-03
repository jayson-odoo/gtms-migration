"""linkages / master_incoterms — exporter. Upsert on code."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_incoterms',
        conflict_cols=['code'],
        update_cols=['description', 'basis_port', 'mode_of_transport', 'quality_basis',
                     'weight_basis', 'is_require_location', 'can_sea_discharge', 'is_active'],
        mode='update_insert',
        require_non_null=['code', 'basis_port', 'mode_of_transport', 'quality_basis', 'weight_basis'],
    )
