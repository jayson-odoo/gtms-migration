"""additional-charges / master_additional_cost_groups — loader (tab 'Additional Cost Group')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_additional_cost_groups(**kwargs):
    return read_tab('Additional Cost Group')
