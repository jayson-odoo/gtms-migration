"""legal-entity / master_payment_terms — loader (Google Sheets Reader #51, tab 'Payment Term')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_payment_terms(**kwargs):
    return read_tab('Payment Term')
