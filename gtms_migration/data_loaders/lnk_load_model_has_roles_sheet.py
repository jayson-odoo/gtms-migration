"""linkages / model_has_roles — loader (tab 'User Roles')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_model_has_roles(**kwargs):
    return read_tab('User Roles')
