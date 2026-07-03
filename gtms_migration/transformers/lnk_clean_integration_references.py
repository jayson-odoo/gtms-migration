"""linkages / master_integration_references — transformer + FK resolution.

Each row maps an external-system reference (vendor/customer ref no) to an internal record.
All rows are integratable_type 'App\\Models\\Counterparty'. The counterparty is resolved by
(name + legal_entity) — NOT name alone — because the same company trades under both legal
entities (QL Feed + QL International) with the same name but different M3 codes; resolving by
name only would collapse both onto one counterparty. external_system_id is the single 'M3'.
"""
from gtms_migration.utils.blocks import clean_df, resolve_fk, resolve_fk_composite

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={
        'Vendor Reference': 'vendor_reference_no',
        'Customer Reference': 'customer_reference_no',
        'Integratable Reference': 'cp_name',
        'Integratable Legal Entity': 'legal_entity_id',
        'Integratable Type': 'integratable_type',
    })
    df = clean_df(
        df,
        cols=['cp_name', 'legal_entity_id', 'integratable_type',
              'vendor_reference_no', 'customer_reference_no'],
        key_cols=['cp_name', 'legal_entity_id', 'integratable_type'],
        null_cols=['vendor_reference_no', 'customer_reference_no'],
    )
    # legal-entity name -> id, then composite (name, legal_entity_id) -> counterparty id
    # (disambiguates same-name counterparties across QL Feed / QL International).
    df = resolve_fk(df, 'legal_entity_id', 'master_legal_entities', 'name')
    df = resolve_fk_composite(df, 'integratable_id', 'master_counterparties',
                              ['name', 'legal_entity_id'], ['cp_name', 'legal_entity_id'])
    # Single external system 'M3' for all references; resolve its id (avoids hard-coding).
    df['external_system_id'] = 'M3'
    df = resolve_fk(df, 'external_system_id', 'master_external_systems', 'code')
    return df
