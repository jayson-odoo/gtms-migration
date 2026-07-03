"""legal-entity / master_counterparties (Profit Centers) — validation block."""
from gtms_migration.utils.validate import validate_to_sheets

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom


@custom
def validate(df, **kwargs):
    # Profit centers are the only counterparties that carry an M3 code (code IS NOT NULL);
    # the codeless rows are owned by the cpl Counterparty v2 check. Scoping here keeps the
    # two populations from showing up as "extra" in each other's count.
    return validate_to_sheets(
        sheet_df=df,
        db_table='master_counterparties',
        keys=['code'],
        check_name='is_profit_centers_passed',
        field_tab='Counterparty Field Level Validator',
        fk_checks=[{'col': 'country', 'ref_table': 'master_countries', 'ref_col': 'code'}],
        db_where='code IS NOT NULL',
    )
