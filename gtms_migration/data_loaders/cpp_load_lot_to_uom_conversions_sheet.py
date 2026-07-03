"""counterparty-products / master_lot_to_uom_conversions — loader (tab 'Product Lot to UoM Conversion')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_lot_to_uom_conversions(**kwargs):
    return read_tab('Product Lot to UoM Conversion')
