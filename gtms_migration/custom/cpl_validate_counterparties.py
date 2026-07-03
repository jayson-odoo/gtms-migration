"""counterparty-location / master_counterparties — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    # The Counterparty v2 sheet owns the rows with no M3 code (code IS NULL) — both external
    # counterparties (is_internal=false) and internal entities (is_internal=true). The 2 rows
    # with a code are le Profit Centers (validated separately), so scoping to code IS NULL
    # validates all of this sheet's rows AND drops those 2 from the "extra" count.
    return validate_to_sheets(
        sheet_df=df, db_table='master_counterparties', keys=['legal_entity_id', 'name'],
        check_name='is_counterparty_v2_passed', field_tab='Counterparty v2 Field Level Validator',
        fk_checks=[{'col': 'country', 'ref_table': 'master_countries', 'ref_col': 'code'}],
        db_where='code IS NULL',
    )
