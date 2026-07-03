"""linkages / contract_term_products — loader (tab 'Contract Term x Product')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_contract_term_products(**kwargs):
    return read_tab('Contract Term x Product')
