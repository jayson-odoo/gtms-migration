"""counterparty-products / master_price_indexes — exporter."""
from gtms_migration.utils.blocks import export_table

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, **kwargs):
    return export_table(
        df, 'master_price_indexes',
        conflict_cols=['code'],
        update_cols=['description', 'month', 'contract_type_id', 'application', 'source_id', 'is_integration', 'ticker_code', 'currency', 'incoterm_id', 'uom_id', 'basis_port_id', 'forward_months', 'is_active'],
        mode='on_conflict',
        fk_filters=[('currency', 'master_currencies', 'code'), ('contract_type_id', 'master_contract_types', 'id'), ('incoterm_id', 'master_incoterms', 'id'), ('basis_port_id', 'master_ports', 'id')],
        require_non_null=[],
    )
