"""linkages / counterparty_users — loader (tab 'User x Profit Center')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_counterparty_users(**kwargs):
    return read_tab('User x Profit Center')
