"""linkages / inventory_location_packaging_fees — loader (tab 'Inventory Location Packing Charges')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_inventory_location_packaging_fees(**kwargs):
    return read_tab('Inventory Location Packing Charges')
