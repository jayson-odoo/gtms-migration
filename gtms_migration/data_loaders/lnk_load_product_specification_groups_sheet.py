"""linkages / product_specification_groups — loader (tab 'Spec Group x Product')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_product_specification_groups(**kwargs):
    return read_tab('Spec Group x Product')
