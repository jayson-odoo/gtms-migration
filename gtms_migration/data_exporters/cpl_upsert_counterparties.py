"""counterparty-location / master_counterparties — exporter.

True identity is (legal_entity_id, lower(name)) — the 411 sheet rows already exist
under different codes. Match on (legal_entity_id, name) case-insensitively and update
the descriptive fields. `code` (M3 Code) is intentionally NOT written here: the source
M3 codes contain 19 duplicates that would violate master_counterparties_code_unique.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

UPDATE_COLS = ['long_name', 'counterparty_group_id', 'is_internal',
               'company_registration_number', 'tax_registration_number', 'tin_no', 'address',
               'country', 'billing_address', 'billing_country', 'phone', 'fax', 'website', 'reference_1',
               'reference_2']


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_counterparties',
        conflict_cols=['legal_entity_id', 'name'],
        update_cols=UPDATE_COLS,
        mode='update_insert',
        fk_filters=[('country', 'master_countries', 'code'),
                    ('billing_country', 'master_countries', 'code')],
        require_non_null=['legal_entity_id'],
        ci_cols=['name'],
    )
