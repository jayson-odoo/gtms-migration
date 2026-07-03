"""legal-entity / master_legal_entities — exporter. DB Merger (#22).
match=code (unique) -> on_conflict. business_unit_id NOT NULL. country/billing_country/currency FK-filtered.
"""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

UPDATE_COLS = ['name', 'short_name', 'is_active', 'business_unit_id',
               'company_registration_number', 'tax_registration_number', 'tin_number',
               'currency', 'timezone', 'website', 'logo', 'printout_logo', 'language',
               'contract_number_format', 'billing_number_format', 'address_id',
               'billing_address_id', 'phone', 'fax', 'country', 'billing_country']


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_legal_entities',
        conflict_cols=['code'],
        update_cols=UPDATE_COLS,
        mode='on_conflict',
        fk_filters=[('country', 'master_countries', 'code'),
                    ('billing_country', 'master_countries', 'code'),
                    ('currency', 'master_currencies', 'code')],
        require_non_null=['business_unit_id'],
    )
