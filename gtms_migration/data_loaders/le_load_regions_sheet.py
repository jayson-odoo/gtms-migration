"""legal-entity / master_regions — data loader.

Tab "Regions". master_regions is otherwise pre-seeded by the app; this pipeline
migrates it from the sheet so a from-scratch run_all has regions available for
downstream consumers (e.g. master_ports resolves region_id -> master_regions.name).
Reads the raw sheet tab as strings; typing/cleaning happens downstream.
"""
from gtms_migration.utils.sheets import read_tab

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_regions(**kwargs):
    return read_tab('Regions')


@test
def test_output(df) -> None:
    assert df is not None and not df.empty, 'Regions sheet returned no rows'
    for col in ['id', 'name', 'is_active']:
        assert col in df.columns, f'Missing expected column: {col}'
