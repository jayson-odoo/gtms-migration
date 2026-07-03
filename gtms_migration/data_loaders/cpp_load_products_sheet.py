"""counterparty-products / master_products — loader (tab 'Products')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_products(**kwargs):
    return read_tab('Products')
