"""Postgres helpers for the GTMS migration.

`upsert` replicates KNIME's DB Merger: insert rows, and on conflict over the
business-key column(s) update only the specified columns. Connection settings
come from io_config.yaml (which reads the repo-root .env).
"""
import os
from datetime import datetime, timezone

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values


def get_connection():
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_DATABASE'],
        user=os.environ['DB_USERNAME'],
        password=os.environ['DB_PASSWORD'],
        connect_timeout=10,
    )


def _norm_key(v):
    """Normalize a key value for set-membership comparison between sheet and DB:
    numbers compare numerically (1 == 1.0), text compares stripped+lowercased, NA -> None."""
    if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)):
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v) if str(v).strip().lstrip('-').replace('.', '', 1).isdigit() else str(v).strip().lower()
    except Exception:
        return str(v).strip().lower()


def prune_to_keys(table: str, conflict_cols, sheet_df: pd.DataFrame, schema: str = 'public',
                  dry: bool = True) -> tuple:
    """Delete DB rows in `table` whose business key (conflict_cols) is NOT present in
    `sheet_df` (the authoritative sheet rows just upserted). Per-row, autocommit, FK-blocked
    rows are caught and skipped (kept). dry=True only reports. Returns (deleted, skipped, blocked_samples)."""
    conflict_cols = list(conflict_cols)
    sheet_keys = set()
    for _, r in sheet_df[conflict_cols].iterrows():
        sheet_keys.add(tuple(_norm_key(r[c]) for c in conflict_cols))

    conn = get_connection()
    conn.autocommit = True
    try:
        cur = conn.cursor()
        sel = ', '.join(f'"{c}"' for c in conflict_cols)
        cur.execute(f'select {sel} from "{schema}"."{table}"')
        db_rows = cur.fetchall()
        orphans = [row for row in db_rows if tuple(_norm_key(v) for v in row) not in sheet_keys]
        deleted = skipped = 0
        blocked = []
        where = ' AND '.join(f'"{c}" = %s' for c in conflict_cols)
        for row in orphans:
            if any(v is None for v in row):  # can't safely target a NULL key; leave it
                skipped += 1
                continue
            if dry:
                deleted += 1
                continue
            try:
                cur.execute(f'delete from "{schema}"."{table}" where {where}', row)
                deleted += 1
            except Exception as e:
                skipped += 1
                if len(blocked) < 3:
                    blocked.append(str(e).splitlines()[0][:70])
        verb = 'would delete' if dry else 'deleted'
        print(f'[{table}] prune ({"DRY" if dry else "LIVE"}): {verb} {deleted} orphan(s), '
              f'kept {skipped} (FK-blocked/NULL-key)'
              + (f' e.g. {blocked}' if blocked else ''))
        return deleted, skipped, blocked
    finally:
        conn.close()


def read_sql(sql: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def _py(v):
    """NaN/NaT -> SQL NULL; numpy scalars (int64/bool_) -> native Python for psycopg2."""
    if pd.isna(v):
        return None
    return v.item() if hasattr(v, 'item') else v


def upsert(df: pd.DataFrame, table: str, conflict_cols, update_cols, schema: str = 'public',
           set_timestamps_on_insert=None, backfill_timestamps=None, mode: str = 'on_conflict',
           ci_cols=()) -> int:
    """Replicate KNIME's DB Merger: insert rows, and on a business-key match update
    only `update_cols` (KNIME's setDataColumns); unlisted columns keep their value.

    mode:
      'on_conflict'   — INSERT ... ON CONFLICT (conflict_cols) DO UPDATE. Fast/atomic;
                        requires a unique index on conflict_cols.
      'update_insert' — per-row UPDATE ... WHERE conflict_cols; INSERT if no row matched.
                        No unique index needed — use when the table lacks one.

    `set_timestamps_on_insert`: timestamp columns set to now() on INSERT.
    `backfill_timestamps`: timestamp columns filled on UPDATE via COALESCE(col, now()) —
        fixes pre-existing NULLs without churning rows that already have a value.
    Returns the number of rows processed.
    """
    if df.empty:
        return 0
    df = df.copy()
    # Surrogate primary key: never write an explicit `id` unless it IS the conflict key.
    # A sheet-provided id can collide with an existing row's PK on an independently-seeded
    # database (e.g. prod), and ON CONFLICT on a *natural* key won't absorb a PK(id) clash.
    # Drop it so the sequence assigns ids on insert and existing rows match by natural key.
    if 'id' in df.columns and 'id' not in [str(c) for c in conflict_cols]:
        df = df.drop(columns=['id'])
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    set_ts = list(set_timestamps_on_insert or [])
    backfill_ts = list(backfill_timestamps or [])
    for c in set_ts:
        df[c] = now  # INSERT value

    cols = list(df.columns)
    conflict_cols = list(conflict_cols)
    update_cols = list(update_cols)
    rows = [tuple(_py(v) for v in r) for r in df.itertuples(index=False, name=None)]

    if mode == 'on_conflict':
        col_sql = ', '.join(f'"{c}"' for c in cols)
        conflict_sql = ', '.join(f'"{c}"' for c in conflict_cols)
        set_parts = [f'"{c}" = EXCLUDED."{c}"' for c in update_cols]
        set_parts += [f'"{c}" = COALESCE("{table}"."{c}", EXCLUDED."{c}")' for c in backfill_ts]
        # A pure junction (no update_cols, no timestamps) has nothing to SET on conflict —
        # an empty DO UPDATE SET is invalid SQL, so keep the existing row with DO NOTHING.
        conflict_action = f'DO UPDATE SET {", ".join(set_parts)}' if set_parts else 'DO NOTHING'
        sql = (
            f'INSERT INTO "{schema}"."{table}" ({col_sql}) VALUES %s '
            f'ON CONFLICT ({conflict_sql}) {conflict_action}'
        )
        conn = get_connection()
        try:
            with conn, conn.cursor() as cur:
                execute_values(cur, sql, rows, page_size=1000)
            return len(rows)
        finally:
            conn.close()

    elif mode == 'update_insert':
        set_parts = [f'"{c}" = %s' for c in update_cols]
        set_parts += [f'"{c}" = COALESCE("{c}", %s)' for c in backfill_ts]
        # Type-aware match: numeric keys compared numerically (1 == 1.0); text keys
        # trimmed (source DB names often carry trailing spaces). Avoids near-dup inserts.
        import pandas.api.types as ptypes
        numeric_key = {c: ptypes.is_numeric_dtype(df[c]) for c in conflict_cols}
        ci_cols = set(ci_cols)

        def where_part(c):
            if numeric_key[c]:
                return f'"{c}" = %s'
            if c in ci_cols:  # case-insensitive (matches a LOWER(...) functional unique index)
                return f'LOWER(TRIM("{c}"::text)) = LOWER(%s)'
            return f'TRIM("{c}"::text) = %s'

        where_sql = ' AND '.join(where_part(c) for c in conflict_cols)
        insert_col_sql = ', '.join(f'"{c}"' for c in cols)
        insert_ph = ', '.join(['%s'] * len(cols))
        update_sql = f'UPDATE "{schema}"."{table}" SET {", ".join(set_parts)} WHERE {where_sql}'
        insert_sql = f'INSERT INTO "{schema}"."{table}" ({insert_col_sql}) VALUES ({insert_ph})'
        conn = get_connection()
        try:
            with conn, conn.cursor() as cur:
                for r in rows:
                    rowd = dict(zip(cols, r))
                    where_vals = [rowd[c] if numeric_key[c] else (None if rowd[c] is None else str(rowd[c]).strip())
                                  for c in conflict_cols]
                    params = [rowd[c] for c in update_cols] + [now] * len(backfill_ts) + where_vals
                    cur.execute(update_sql, params)
                    if cur.rowcount == 0:
                        cur.execute(insert_sql, r)
            return len(rows)
        finally:
            conn.close()

    raise ValueError(f'unknown upsert mode: {mode}')
