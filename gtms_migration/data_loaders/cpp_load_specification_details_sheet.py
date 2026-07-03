"""counterparty-products / master_specification_details — loader (tab 'Spec Group Spec')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_specification_details(**kwargs):
    return read_tab('Spec Group Spec')
