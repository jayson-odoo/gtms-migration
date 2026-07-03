"""legal-entity / master_document_content_snippets — loader (Google Sheets Reader #44, tab 'Document Content Snippet')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_document_content_snippets(**kwargs):
    return read_tab('Document Content Snippet')
