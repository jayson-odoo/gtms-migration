"""acl / users — exporter. Upsert on `email` (users_email_unique).

New users get a bcrypt placeholder password: the real hash is unknown, so this forces a
forgot-password reset on first login. Existing users keep their current password because
`password` is not in update_cols (ON CONFLICT only touches the listed columns).

`code` is UNIQUE in the DB. Any in-batch duplicate code, or a code already taken by a
different user, is dropped and reported here so one bad row can't abort the whole insert.
"""
import pandas as pd

from gtms_migration.utils.pg import read_sql, upsert

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

TABLE = 'users'
# Bcrypt hash ($2y$, Laravel-compatible) of an unknown random secret -> unusable until reset.
PLACEHOLDER_PASSWORD = '$2y$10$bIMc14coqQB/GIryvmRlZ.0QSTuh1LVPSMFTZVowAYvhxUVH140iK'
UPDATE_COLS = ['name', 'timezone', 'is_active',
               'password_expired_at', 'valid_from', 'valid_to', 'code']


@data_exporter
def export_data(df, **kwargs):
    out = df.copy()
    out['password'] = PLACEHOLDER_PASSWORD

    # Enforce the unique `code` index before insert: drop in-batch dup codes (keep first)
    # and any code already held by a *different* email. Exclude DB rows whose email is in
    # this batch — their code gets overwritten to the sheet value, so their old code is
    # being vacated (avoids a stale-snapshot false positive when a code is reassigned).
    batch_emails = set(out['email'].astype(str))
    existing = read_sql("select code, email from users where code is not null")
    taken = {c: e for c, e in zip(existing['code'].astype(str), existing['email'].astype(str))
             if e not in batch_emails}
    code_notna = out['code'].notna()
    dup_in_batch = code_notna & out['code'].astype(str).where(code_notna).duplicated(keep='first').fillna(False)
    collide_db = out.apply(
        lambda r: pd.notna(r['code']) and taken.get(str(r['code']), str(r['email'])) != str(r['email']),
        axis=1)
    bad = dup_in_batch | collide_db
    if bad.any():
        for _, r in out[bad].iterrows():
            print(f'[{TABLE}] SKIPPED {r["name"]} <{r["email"]}> — duplicate code '
                  f'{r["code"]!r}; make it unique in the sheet and re-run')
    out = out[~bad]

    n = upsert(
        out, TABLE,
        conflict_cols=['email'],
        update_cols=UPDATE_COLS,
        set_timestamps_on_insert=['created_at', 'updated_at'],
        backfill_timestamps=['created_at', 'updated_at'],
        mode='on_conflict',
    )
    print(f'[{TABLE}] upserted {n} rows (conflict=email); password set on insert only')
    return df  # full sheet df (incl. any dropped rows) so the validator reports honestly
