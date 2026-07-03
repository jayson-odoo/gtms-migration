"""linkages / master_price_build_up_components — loader (tab 'Price Buildup Component')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_price_build_up_components(**kwargs):
    return read_tab('Price Buildup Component')
