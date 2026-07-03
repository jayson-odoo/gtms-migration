"""counterparty-location / master_counterparties — transformer + FK resolution.

Source: 'Counterparty v2' tab (434 rows). Keep only Unique rows. 'type' (External/
QL/Farms) maps to is_internal (internal = not External) AND counterparty_group_id
(resolved from master_counterparty_groups.name). legal_entity_id holds a legal-entity
name -> resolved to id. code <- 'M3 Code'. Merge key: (name, legal_entity_id).
"""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer

COLS = ['name', 'long_name', 'legal_entity_id', 'counterparty_group_id', 'is_internal',
        'company_registration_number', 'tax_registration_number', 'tin_no', 'address', 'country',
        'billing_address', 'billing_country', 'phone', 'fax', 'website', 'reference_1', 'reference_2']
NULLABLE = ['long_name', 'company_registration_number', 'tax_registration_number', 'tin_no',
            'address', 'billing_address', 'billing_country', 'phone', 'fax', 'website', 'reference_1',
            'reference_2']


@transformer
def transform(df, *args, **kwargs):
    # Include BOTH Unique and Duplicate rows: the 'Duplicate' flag marks a shared M3 Code, but
    # counterparty keys on (legal_entity_id, name) and does NOT write `code`, so a duplicate M3 code
    # is harmless here (the M3 code is used in Integration Reference, not on the counterparty row).
    df = df[df['Unique / Duplicate'].astype(str).str.strip().str.lower().isin(['unique', 'duplicate'])].copy()
    # is_internal comes straight from the sheet's authoritative is_internal column (do NOT
    # derive it from `type`: the QL/Farms counterparties are still is_internal=false; the
    # real profit centers come from the Profit Centers sheet via the le pipeline).
    df = df.rename(columns={'M3 Code': 'code', 'type': 'counterparty_group_id'})
    df = clean_df(df, cols=COLS, key_cols=['name', 'legal_entity_id'],
                  bool_cols=['is_internal'], null_cols=NULLABLE)
    df = resolve_fk(df, 'counterparty_group_id', 'master_counterparty_groups', 'name')
    df = resolve_fk(df, 'legal_entity_id', 'master_legal_entities', 'name')
    return df
