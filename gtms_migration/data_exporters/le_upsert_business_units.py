"""legal-entity / master_business_units — exporter. DB Merger (#7).
match=id (PK, unique) -> on_conflict. country FK-filtered.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_business_units',
        conflict_cols=['id'],
        update_cols=['name', 'country'],
        mode='on_conflict',
        fk_filters=[('country', 'master_countries', 'code')],
    )
