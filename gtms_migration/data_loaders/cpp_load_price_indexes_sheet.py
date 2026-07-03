"""counterparty-products / master_price_indexes — loader (tab 'Price Index')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_price_indexes(**kwargs):
    return read_tab('Price Index')
