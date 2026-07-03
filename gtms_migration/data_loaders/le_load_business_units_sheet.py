"""legal-entity / master_business_units — loader (Google Sheets Reader #1, tab 'Business Units')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_business_units(**kwargs):
    return read_tab('Business Units')
