"""counterparty-location / master_counterparty_groups — loader (tab 'Counterparty Group')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_counterparty_groups(**kwargs):
    return read_tab('Counterparty Group')
