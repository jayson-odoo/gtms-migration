"""legal-entity / master_legal_entities — transformer + FK resolution.

Resolves three name/string references to surrogate ids:
  business_unit_id   <- master_business_units.name
  address_id         <- addresses.address
  billing_address_id <- addresses.address
country / billing_country / currency stay as codes (FK-filtered at export).
Merge key: code.
"""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

COLS = ['id', 'code', 'name', 'short_name', 'is_active', 'business_unit_id',
        'company_registration_number', 'tax_registration_number', 'tin_number',
        'currency', 'timezone', 'website', 'logo', 'printout_logo', 'language',
        'contract_number_format', 'billing_number_format', 'address_id',
        'billing_address_id', 'phone', 'fax', 'country', 'billing_country']

NULLABLE = ['short_name', 'company_registration_number', 'tax_registration_number',
            'tin_number', 'currency', 'timezone', 'website', 'logo', 'printout_logo',
            'language', 'contract_number_format', 'billing_number_format', 'phone',
            'fax', 'billing_country']


@transformer
def transform(df, *args, **kwargs):
    df = clean_df(df, cols=COLS, key_cols=['code'], int_cols=['id'],
                  bool_cols=['is_active'], null_cols=NULLABLE)
    df = resolve_fk(df, 'business_unit_id', 'master_business_units', 'name')
    df = resolve_fk(df, 'address_id', 'addresses', 'address')
    df = resolve_fk(df, 'billing_address_id', 'addresses', 'address')
    return df
