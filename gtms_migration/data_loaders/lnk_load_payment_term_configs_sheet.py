"""linkages / payment_term_configs — loader (tab 'Payment Term Configs')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_payment_term_configs(**kwargs):
    return read_tab('Payment Term Configs')
