"""linkages / contract_term_incoterms — transformer + FK resolution (junction)."""
from gtms_migration.utils.blocks import clean_df, resolve_fk

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.rename(columns={'contract_term': 'contract_term_id', 'incoterm': 'incoterm_id'})
    df = clean_df(df, cols=['contract_term_id', 'incoterm_id'],
                  key_cols=['contract_term_id', 'incoterm_id'])
    df = resolve_fk(df, 'contract_term_id', 'master_contract_terms', 'name')
    df = resolve_fk(df, 'incoterm_id', 'master_incoterms', 'code')
    return df
