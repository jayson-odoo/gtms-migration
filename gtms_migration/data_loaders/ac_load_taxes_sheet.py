"""additional-charges / master_taxes — loader (tab 'Tax')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_taxes(**kwargs):
    return read_tab('Tax')
