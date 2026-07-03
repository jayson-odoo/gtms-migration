"""legal-entity / master_counterparties — transformer + FK resolution.

Source: Profit Centers tab. The sheet 'id' is dropped (DB id is serial; the 503
existing counterparties have their own ids). The 'phone ' header has a trailing
space. legal_entity_id holds a legal-entity NAME -> resolved to master_legal_entities.id.
Merge key: code.
"""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

COLS = ['code', 'name', 'long_name', 'legal_entity_id', 'company_registration_number',
        'address', 'country', 'phone', 'fax', 'website', 'is_internal', 'is_active']

NULLABLE = ['long_name', 'company_registration_number', 'address', 'phone', 'fax', 'website']


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'phone ': 'phone'})  # source header has a trailing space
    df = clean_df(df, cols=COLS, key_cols=['code'],
                  bool_cols=['is_internal', 'is_active'], null_cols=NULLABLE)
    df = resolve_fk(df, 'legal_entity_id', 'master_legal_entities', 'name')
    return df
