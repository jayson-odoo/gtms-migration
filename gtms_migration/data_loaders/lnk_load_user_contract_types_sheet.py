"""linkages / user_contract_types — loader (tab 'User Contract Type')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_user_contract_types(**kwargs):
    return read_tab('User Contract Type')
