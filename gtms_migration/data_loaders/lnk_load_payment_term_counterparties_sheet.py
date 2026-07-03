"""linkages / payment_term_counterparties — loader (tab 'Payment Term x Profit Center')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_payment_term_counterparties(**kwargs):
    return read_tab('Payment Term x Profit Center')
