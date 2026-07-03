"""legal-entity / master_counterparties — loader (Google Sheets Reader #26, tab 'Profit Centers').

Profit centers are internal counterparties (is_internal=true), upserted into master_counterparties.
"""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_profit_centers(**kwargs):
    return read_tab('Profit Centers')
