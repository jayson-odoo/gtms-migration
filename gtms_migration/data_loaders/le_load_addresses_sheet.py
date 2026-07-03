"""legal-entity / addresses — data loader (KNIME Google Sheets Reader #123, tab 'Addresses')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_addresses(**kwargs):
    return read_tab('Addresses')
