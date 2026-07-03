"""linkages / counterparty_products — loader (tab 'Profit Center x Product')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_counterparty_products(**kwargs):
    return read_tab('Profit Center x Product')
