"""legal-entity / addresses — exporter. DB Merger (#124) -> addresses.
match=(address,city,postcode,state), update=country. No unique index -> update_insert.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'addresses',
        conflict_cols=['address', 'city', 'postcode', 'state'],
        update_cols=['country'],
        mode='update_insert',
        fk_filters=[('country', 'master_countries', 'code')],
    )
