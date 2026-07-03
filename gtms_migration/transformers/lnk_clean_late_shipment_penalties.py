"""linkages / master_late_shipment_penalties — transformer. Standalone master (no FKs).
Merge key: the day range (lower_bound_days, upper_bound_days)."""
from gtms_migration.utils.blocks import clean_df

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer


@transformer
def transform(df, *args, **kwargs):
    return clean_df(
        df,
        cols=['lower_bound_days', 'upper_bound_days', 'penalty_percentage', 'is_active'],
        key_cols=['lower_bound_days', 'upper_bound_days'],
        int_cols=['lower_bound_days', 'upper_bound_days'],
        float_cols=['penalty_percentage'],
        bool_cols=['is_active'],
    )
