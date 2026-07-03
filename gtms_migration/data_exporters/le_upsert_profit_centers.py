"""legal-entity / master_counterparties — exporter. DB Merger (#29).
match=code (unique) -> on_conflict. legal_entity_id resolved (nullable). country FK-filtered.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

UPDATE_COLS = ['name', 'long_name', 'legal_entity_id', 'company_registration_number',
               'address', 'country', 'phone', 'fax', 'website', 'is_internal', 'is_active']


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_counterparties',
        conflict_cols=['code'],
        update_cols=UPDATE_COLS,
        mode='on_conflict',
        fk_filters=[('country', 'master_countries', 'code')],
    )
