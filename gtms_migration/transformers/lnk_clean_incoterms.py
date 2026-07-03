"""linkages / master_incoterms — transformer. Standalone master, key = code."""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    return clean_df(
        df,
        cols=['code', 'description', 'basis_port', 'mode_of_transport', 'quality_basis',
              'weight_basis', 'is_require_location', 'can_sea_discharge', 'is_active'],
        key_cols=['code'],
        bool_cols=['is_require_location', 'can_sea_discharge', 'is_active'],
        null_cols=['description'],
    )
