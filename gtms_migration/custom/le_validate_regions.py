"""legal-entity / master_regions — validation block.

Runs after the upsert. Compares the cleaned sheet rows against the DB table and
writes two reports to Google Sheets:
  - 'Regions Field Level Validator'  (per-row field comparison + timestamps)
  - 'Row Count Validator'            (this table's pass/justification line)
"""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_regions',
        keys=['name'],
        check_name='is_regions_passed',
        field_tab='Regions Field Level Validator',
    )


@test
def test_output(report) -> None:
    assert report is not None and not report.empty, 'Validation produced no report'
    assert 'field_level_validated' in report.columns
