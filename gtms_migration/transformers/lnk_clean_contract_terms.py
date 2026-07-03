"""linkages / master_contract_terms — transformer. Standalone master (no FKs). Merge key: name.
The sheet uses a literal '[NULL]' marker for empty cells -> normalize to blank first."""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    df = df.replace(r'^\s*\[NULL\]\s*$', '', regex=True)  # literal [NULL] -> blank
    return clean_df(
        df,
        cols=['name', 'basis_weight', 'description', 'fulfillment_tolerance_type',
              'fulfillment_tolerance_value', 'settlement_tolerance_value', 'is_active'],
        key_cols=['name'],
        bool_cols=['is_active'],
        float_cols=['fulfillment_tolerance_value', 'settlement_tolerance_value'],
        null_cols=['basis_weight', 'description', 'fulfillment_tolerance_type'],
    )
