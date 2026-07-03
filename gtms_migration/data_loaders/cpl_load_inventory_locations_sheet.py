"""counterparty-location / master_inventory_locations — loader (tab 'Inventory Locations')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_inventory_locations(**kwargs):
    return read_tab('Inventory Locations')
