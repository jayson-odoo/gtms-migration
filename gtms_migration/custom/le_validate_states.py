"""legal-entity / master_states — validation block (runs after upsert)."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@custom
def validate(df, **kwargs):
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_states',
        keys=['name', 'country'],
        check_name='is_states_passed',
        field_tab='States Field Level Validator',
        fk_checks=[{'col': 'country', 'ref_table': 'master_countries', 'ref_col': 'code'}],
    )


@test
def test_output(report) -> None:
    assert report is not None and not report.empty, 'Validation produced no report'
    assert 'field_level_validated' in report.columns
