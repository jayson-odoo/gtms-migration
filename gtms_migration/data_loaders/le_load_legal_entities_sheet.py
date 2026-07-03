"""legal-entity / master_legal_entities — loader (Google Sheets Reader #20, tab 'Legal Entity')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_legal_entities(**kwargs):
    return read_tab('Legal Entity')
