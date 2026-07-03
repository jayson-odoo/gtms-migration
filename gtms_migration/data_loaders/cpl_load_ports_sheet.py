"""counterparty-location / master_ports — loader (tab 'Ports')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_ports(**kwargs):
    return read_tab('Ports')
