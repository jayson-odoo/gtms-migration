"""counterparty-products / master_uom_conversions — loader (tab 'Product UoM Conversion')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_uom_conversions(**kwargs):
    return read_tab('Product UoM Conversion')
