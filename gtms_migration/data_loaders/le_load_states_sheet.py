"""legal-entity / master_states — data loader.

KNIME node: Google Sheets Reader (#15), tab "States".
"""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_states(**kwargs):
    return read_tab('States')


@test
def test_output(df) -> None:
    assert df is not None and not df.empty, 'States sheet returned no rows'
    for col in ['id', 'name', 'country', 'is_active']:
        assert col in df.columns, f'Missing expected column: {col}'
