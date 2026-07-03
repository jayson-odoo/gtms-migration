"""additional-charges / master_additional_costs — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_additional_costs', conflict_cols=['name'], update_cols=['description', 'additional_cost_group_id', 'value_type', 'default_value', 'account_id', 'transaction_type', 'profit_centers', 'contract_types', 'charges_type', 'is_active'],
        mode='update_insert', fk_filters=[], require_non_null=[], ci_cols=[],
    )
