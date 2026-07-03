"""legal-entity / master_document_templates — loader (Google Sheets Reader #41, tab 'Document Template')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_document_templates(**kwargs):
    return read_tab('Document Template')
