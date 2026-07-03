"""Per-pipeline validation for the GTMS migration.

Reproduces the KNIME validators, baked into each pipeline:
  1. Row count  — is every sheet row present in the DB table?
  2. Field level — for each sheet row, do all fields match the DB row?
  3. Timestamps — does every DB row have created_at and updated_at?

Writes a per-table field-level report to its '<X> Field Level Validator' tab and
updates this table's line in the shared 'Row Count Validator' tab.
"""
import json
from datetime import datetime, timedelta, timezone

import pandas as pd

from gtms_migration.utils.pg import read_sql

# Column header used for the "when was this validated" stamp, on both the field-level
# report tabs and the shared Row Count Validator tab. Defined once so every pipeline
# (all call validate_to_sheets) gets it identically.
CHECKED_AT_COL = 'checked_at'


def _checked_at() -> str:
    """Current validation time in Malaysia (Asia/Kuala_Lumpur, UTC+8, no DST) — all the
    source data and users are KL-based, so a local stamp is least surprising to readers."""
    return datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
from gtms_migration.utils.sheets import overwrite_tab, upsert_row_count_validator


def _norm(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower()


_EMPTY = {'', 'nan', 'none', 'nat', '<na>'}


def _is_empty(s: pd.Series) -> pd.Series:
    return s.isna() | _norm(s).isin(_EMPTY)


def _values_equal(a: pd.Series, b: pd.Series) -> pd.Series:
    """Equal if any of: both empty (NA vs NULL); normalised strings match; both parse
    to the same number (120 == 120.0 — DB upcasts int cols to float when NULLs present);
    both parse to the same datetime ('2026-01-01 0:00:00' == '2026-01-01 00:00:00')."""
    str_eq = _norm(a) == _norm(b)
    na, nb = pd.to_numeric(a, errors='coerce'), pd.to_numeric(b, errors='coerce')
    num_eq = na.notna() & nb.notna() & (na == nb)
    both_empty = _is_empty(a) & _is_empty(b)
    # Only attempt datetime parsing on date-looking strings (avoids '0' -> epoch matches).
    def _dt(s):
        looks = s.astype(str).str.contains(r'\d[-/].*\d|\d:\d', regex=True, na=False)
        return pd.to_datetime(s.where(looks), errors='coerce')
    da, db = _dt(a), _dt(b)
    dt_eq = da.notna() & db.notna() & (da == db)

    # JSON columns: DB returns parsed objects (['1']) vs the sheet's text ('["1"]').
    def _jcanon(s):
        out = []
        for v in s:
            try:
                out.append(json.dumps(json.loads(v) if isinstance(v, str) else v, sort_keys=True))
            except Exception:
                out.append(None)
        return pd.Series(out, index=s.index)
    ja, jb = _jcanon(a), _jcanon(b)
    json_eq = ja.notna() & jb.notna() & (ja == jb)

    return str_eq | num_eq | both_empty | dt_eq | json_eq


def build_report(sheet_df, db_df, keys, id_col='id', ts_cols=('created_at', 'updated_at')):
    keys = list(keys)
    compare = [c for c in sheet_df.columns if c in db_df.columns and c not in keys and c != id_col]
    ts_cols = [t for t in ts_cols if t in db_df.columns]

    # Keep only sheet keys+compare on the left so the sheet's own id doesn't
    # collide with the DB id (we report the DB-assigned id).
    left = sheet_df[keys + compare].copy()
    right = db_df.rename(columns={c: f'{c} (Right)' for c in keys + compare})
    right_keys = [f'{k} (Right)' for k in keys]
    # Normalise join keys so the merge matches across dtypes. Numeric keys join
    # numerically (1 == 1.0); text keys join as stripped strings.
    for k in keys:
        rk = f'{k} (Right)'
        ln, rn = pd.to_numeric(left[k], errors='coerce'), pd.to_numeric(right[rk], errors='coerce')
        if ln.notna().all() and rn.notna().all():
            left[k], right[rk] = ln.astype(float), rn.astype(float)
        else:
            left[k] = left[k].astype(str).str.strip()
            right[rk] = right[rk].astype(str).str.strip()
    merged = left.merge(right, how='left', left_on=keys, right_on=right_keys)

    # "Matched a DB row?" is determined by the joined key (NaN on the right = no match),
    # which is robust even when the business key is itself the id column.
    in_db = merged[right_keys[0]].notna() if right_keys else pd.Series(True, index=merged.index)

    # Field/timestamp checks only apply to rows that actually matched a DB row,
    # so a missing-in-db row isn't double-counted as a field/timestamp problem.
    fields_match = pd.Series(True, index=merged.index)
    mismatched = pd.Series([[] for _ in range(len(merged))], index=merged.index)
    for c in keys + compare:
        eq = _values_equal(merged[c], merged[f'{c} (Right)'])
        fields_match &= eq
        for idx in merged.index[in_db & ~eq]:
            mismatched.at[idx].append(c)
    ts_present = ~merged[ts_cols].isna().any(axis=1) if ts_cols else pd.Series(True, index=merged.index)

    merged['field_level_validated'] = in_db & fields_match & ts_present
    # Which fields differ (sheet vs DB) — surfaced in the report for quick triage.
    merged['mismatched_fields'] = mismatched.apply(lambda lst: ', '.join(lst))
    merged.loc[in_db & ~ts_present, 'mismatched_fields'] = (
        merged.loc[in_db & ~ts_present, 'mismatched_fields']
        .map(lambda s: (s + '; ' if s else '') + 'missing timestamp'))

    order = (keys + compare
             + ([id_col] if id_col in merged.columns else [])
             + right_keys + [f'{c} (Right)' for c in compare]
             + ts_cols + ['field_level_validated', 'mismatched_fields'])
    # Dedupe while preserving order (the business key can itself be the id column).
    seen = set()
    cols_out = [c for c in order if c in merged.columns and not (c in seen or seen.add(c))]
    report = merged[cols_out].copy()

    summary = {
        'sheet_count': len(sheet_df),
        'db_count': len(db_df),
        'row_count_match': len(sheet_df) == len(db_df),
        'missing_in_db': int((~in_db).sum()),
        'field_mismatches': int((in_db & ~fields_match).sum()),
        'ts_missing': int((in_db & ~ts_present).sum()),
    }
    return report, summary


def validate_to_sheets(sheet_df, db_table, keys, check_name, field_tab,
                       id_col='id', schema='public', fk_checks=None, db_where=None):
    """fk_checks: optional list of dicts {'col', 'ref_table', 'ref_col'} — flags sheet
    rows whose `col` value is absent from `ref_table.ref_col` (e.g. a state whose
    `country` is not in master_countries.code).
    db_where: optional SQL predicate restricting which DB rows this check compares against
    — e.g. 'is_internal = false' so the counterparty check ignores profit-center rows that
    a different source owns (pair with a matching sheet_df filter in the caller)."""
    where = f' where {db_where}' if db_where else ''
    db_df = read_sql(f'select * from "{schema}"."{db_table}"{where}')
    report, s = build_report(sheet_df, db_df, keys, id_col=id_col)

    # Stamp this validation run's time on both outputs (one value, both sheets).
    checked_at = _checked_at()
    report[CHECKED_AT_COL] = checked_at
    overwrite_tab(field_tab, report)

    # Fatal checks drive the pass/fail flag.
    reasons = []
    for fk in (fk_checks or []):
        valid = set(read_sql(f'select "{fk["ref_col"]}" from "{schema}"."{fk["ref_table"]}"')[fk['ref_col']].astype(str))
        bad = sheet_df[~sheet_df[fk['col']].astype(str).isin(valid)]
        if len(bad):
            vals = ', '.join(sorted(bad[fk['col']].astype(str).unique())[:5])
            reasons.append(f"{len(bad)} row(s) with non-existent {fk['col']}: {vals}")
    if s['missing_in_db']:
        reasons.append(f"{s['missing_in_db']} sheet row(s) missing in db")
    if s['field_mismatches']:
        reasons.append(f"{s['field_mismatches']} row(s) with field mismatches")
    if s['ts_missing']:
        reasons.append(f"{s['ts_missing']} db row(s) missing created_at/updated_at")
    passed = not reasons

    # Row-count note is informational and does NOT drive pass/fail: the DB is usually a
    # superset of the sheet (pre-existing rows we never delete), which is expected. A real
    # shortfall (sheet rows missing in db) is already flagged above via missing_in_db.
    if s['row_count_match']:
        count_note = f"row count match: sheet={s['sheet_count']} = db={s['db_count']}"
    elif s['db_count'] > s['sheet_count']:
        count_note = (f"row count OK: all {s['sheet_count']} sheet row(s) present; db has "
                      f"{s['db_count'] - s['sheet_count']} extra pre-existing row(s) not in sheet (expected)")
    else:
        count_note = (f"row count SHORT: sheet={s['sheet_count']} vs db={s['db_count']} "
                      f"(db missing {s['sheet_count'] - s['db_count']})")
    justification = '; '.join(reasons + [count_note])

    upsert_row_count_validator(db_table, check_name, passed, justification, checked_at=checked_at)

    print(f"[validate {db_table}] passed={passed} "
          f"sheet={s['sheet_count']} db={s['db_count']} row_count_match={s['row_count_match']} "
          f"missing_in_db={s['missing_in_db']} field_mismatches={s['field_mismatches']} "
          f"ts_missing={s['ts_missing']}")
    return report
