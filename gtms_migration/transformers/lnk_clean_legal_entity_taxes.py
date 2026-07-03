"""linkages / legal_entity_taxes — transformer + FK resolution."""
from gtms_migration.utils.blocks import clean_df, resolve_fk  # noqa: F401

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'name': 'legal_entity_id', 'tax_code': 'tax_id'})
    df = clean_df(df, cols=['legal_entity_id', 'tax_id'], key_cols=['legal_entity_id', 'tax_id'], int_cols=[], bool_cols=[], null_cols=[], float_cols=[])
    df = resolve_fk(df, 'legal_entity_id', 'master_legal_entities', 'name')
    df = resolve_fk(df, 'tax_id', 'master_taxes', 'code')
    return df
