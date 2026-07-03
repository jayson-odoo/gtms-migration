"""linkages / master_integration_references — loader (tab 'Integration Reference')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_integration_references(**kwargs):
    return read_tab('Integration Reference')
