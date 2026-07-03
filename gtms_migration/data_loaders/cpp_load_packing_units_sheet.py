"""counterparty-products / master_packing_units — loader (tab 'Packing Unit')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_packing_units(**kwargs):
    return read_tab('Packing Unit')
