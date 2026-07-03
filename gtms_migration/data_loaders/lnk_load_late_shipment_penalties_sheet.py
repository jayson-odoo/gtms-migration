"""linkages / master_late_shipment_penalties — loader (tab 'Late Shipment Penalty')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_late_shipment_penalties(**kwargs):
    return read_tab('Late Shipment Penalty')
