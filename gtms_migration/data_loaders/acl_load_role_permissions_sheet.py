"""acl / role_has_permissions — loader (tab 'Role Permission')."""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader


@data_loader
def load_role_permissions(**kwargs):
    return read_tab('Role Permission')
