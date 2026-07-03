"""legal-entity / master_countries — data loader.

KNIME node: Google Sheets Reader (#10), tab "Countries".
Reads the raw sheet tab as strings; typing/cleaning happens downstream.
"""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_countries(**kwargs):
    return read_tab('Countries')


@test
def test_output(df) -> None:
    assert df is not None and not df.empty, 'Countries sheet returned no rows'
    for col in ['id', 'code', 'name', 'is_active']:
        assert col in df.columns, f'Missing expected column: {col}'
