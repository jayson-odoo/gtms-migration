"""counterparty-products / master_specifications — loader (tab 'Specifications')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_specifications(**kwargs):
    return read_tab('Specifications')
