"""linkages / legal_entity_contract_types — transformer + FK resolution (junction)."""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'legal_entity': 'legal_entity_id', 'contract_type': 'contract_type_id'})
    df = clean_df(df, cols=['legal_entity_id', 'contract_type_id'],
                  key_cols=['legal_entity_id', 'contract_type_id'])
    df = resolve_fk(df, 'legal_entity_id', 'master_legal_entities', 'name')
    df = resolve_fk(df, 'contract_type_id', 'master_contract_types', 'code')
    return df
