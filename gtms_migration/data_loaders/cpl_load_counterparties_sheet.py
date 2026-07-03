"""counterparty-location / master_counterparties — loader (tab 'Counterparty v2')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_counterparties(**kwargs):
    return read_tab('Counterparty v2')
