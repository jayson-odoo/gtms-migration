"""linkages / master_contract_terms — loader (tab 'Contract Terms')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_contract_terms(**kwargs):
    return read_tab('Contract Terms')
