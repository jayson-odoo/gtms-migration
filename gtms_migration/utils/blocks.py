"""Shared helpers so each per-table block stays a few lines.

clean_df  — select/strip/type-cast sheet columns, drop rows missing a business key.
export_table — filter rows whose FK values don't exist (avoids FK violations,
              reported by the validator), then upsert; returns the full df for the
              downstream validation block.
"""
import os

import pandas as pd

from gtms_migration.utils.pg import prune_to_keys, read_sql, upsert

TRUE_SET = {'true', 't', '1', 'yes', 'y'}

# Tables NEVER pruned: master_counterparties is fed by two sheets (le Profit Centers +
# cpl Counterparty v2), and roles/role_has_permissions carry app-seeded super-admin grants —
# pruning any of these to one sheet would delete legitimate rows / break access.
NO_PRUNE_TABLES = {'master_counterparties', 'roles', 'role_has_permissions'}


def clean_df(df, cols, key_cols, int_cols=(), bool_cols=(), null_cols=(), float_cols=()):
    df = df[list(cols)].copy()
    for c in cols:
        df[c] = df[c].astype(str).str.strip()
    for c in key_cols:
        df = df[df[c] != '']
    for c in int_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')
    for c in float_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    for c in bool_cols:
        df[c] = df[c].astype(str).str.strip().str.lower().isin(TRUE_SET)
    for c in null_cols:  # blank -> NA so nullable (incl. FK) columns write SQL NULL
        df[c] = df[c].replace('', pd.NA)
    return df.reset_index(drop=True)


def resolve_fk_composite(df, new_col, ref_table, ref_cols, src_cols, ref_id_col='id'):
    """Resolve a surrogate id from a multi-column match. Maps df[src_cols] to
    ref_table[ref_cols] (positionally) and writes ref_table.id into df[new_col].
    E.g. spec_detail_id from (specification_group_id, specification_id)."""
    sel = ', '.join(f'"{c}"' for c in list(ref_cols) + [ref_id_col])
    ref = read_sql(f'select {sel} from {ref_table}')
    key = lambda frame, cols: frame[list(cols)].astype(str).apply(lambda r: '\x1f'.join(r.values), axis=1)
    mapping = dict(zip(key(ref, ref_cols), ref[ref_id_col]))
    df = df.copy()
    df[new_col] = key(df, src_cols).map(mapping).astype('Int64')
    return df


def resolve_fk(df, col, ref_table, ref_natural_col, ref_id_col='id', where=None):
    """Replace df[col] — which holds a parent's natural key (a name / address string) —
    with the parent's surrogate id, by looking it up in ref_table. Blank or unresolved
    values become <NA> (written as SQL NULL). Mirrors KNIME's Joiner FK resolution.
    `where`: optional SQL predicate scoping which parent rows are eligible — e.g.
    'code IS NOT NULL' to resolve a name to the profit-center row when the same name also
    exists as a (codeless) counterparty."""
    w = f' where {where}' if where else ''
    ref = read_sql(f'select "{ref_id_col}", "{ref_natural_col}" from {ref_table}{w}')
    mapping = dict(zip(ref[ref_natural_col].astype(str).str.strip(), ref[ref_id_col]))
    df = df.copy()
    df[col] = df[col].astype(str).str.strip().map(mapping).astype('Int64')
    return df


def export_table(df, table, conflict_cols, update_cols, mode='on_conflict', fk_filters=(),
                 require_non_null=(), ci_cols=(), timestamp_cols=('created_at', 'updated_at')):
    """fk_filters: list of (col, ref_table, ref_col). Rows whose value is absent from
    the reference are skipped (and logged) so the insert can't violate the FK.
    require_non_null: columns that must be non-null to insert (e.g. a NOT NULL resolved FK);
    rows with a null there are skipped and logged.
    timestamp_cols: created_at/updated_at columns to stamp on insert + backfill on update;
    pass () for tables that have no timestamp columns (e.g. a pure junction)."""
    keep = pd.Series(True, index=df.index)
    for col, ref_table, ref_col in fk_filters:
        valid = set(read_sql(f'select "{ref_col}" from {ref_table}')[ref_col].astype(str))
        # A null FK is allowed (nullable column -> SQL NULL); only non-null values must exist.
        m = df[col].isna() | df[col].astype(str).isin(valid)
        if (~m).any():
            bad = sorted(df.loc[~m, col].astype(str).unique())[:8]
            print(f'[{table}] skipping {int((~m).sum())} row(s) with non-existent {col}: {bad}')
        keep &= m
    for col in require_non_null:
        m = df[col].notna()
        if (~m).any():
            print(f'[{table}] skipping {int((~m).sum())} row(s) with null {col}')
        keep &= m

    out = df[keep]
    if mode == 'on_conflict':
        # ON CONFLICT can't touch the same row twice in one batch — collapse duplicate
        # business keys (last wins, matching KNIME's row-order merge).
        before = len(out)
        out = out.drop_duplicates(subset=conflict_cols, keep='last')
        if len(out) < before:
            print(f'[{table}] collapsed {before - len(out)} duplicate {conflict_cols} row(s)')

    n = upsert(
        out, table,
        conflict_cols=conflict_cols,
        update_cols=update_cols,
        set_timestamps_on_insert=list(timestamp_cols),
        backfill_timestamps=list(timestamp_cols),
        mode=mode,
        ci_cols=ci_cols,
    )
    print(f'[{table}] upserted {n} rows (conflict={conflict_cols}, update={update_cols})')

    # Opt-in de-pollution: delete DB rows whose business key isn't in the sheet.
    # GTMS_PRUNE='dry' reports only; GTMS_PRUNE='1' deletes (FK-blocked rows are kept).
    prune_mode = os.environ.get('GTMS_PRUNE')
    if prune_mode and table not in NO_PRUNE_TABLES:
        prune_to_keys(table, conflict_cols, out, dry=(prune_mode != '1'))

    return df
