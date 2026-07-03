"""linkages / inventory_location_storage_rates — loader (tab 'Storage Charges')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_inventory_location_storage_rates(**kwargs):
    return read_tab('Storage Charges')
