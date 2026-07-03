"""linkages / contract_term_incoterms — loader (tab 'Contract Term x Incoterm')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_contract_term_incoterms(**kwargs):
    return read_tab('Contract Term x Incoterm')
