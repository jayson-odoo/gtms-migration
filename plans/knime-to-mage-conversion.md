# KNIME → Mage AI Conversion Plan

_Last updated: 2026-06-03_

## Goal

Convert the KNIME workflows under `/Users/skribble/knime-workspace/gtms-dev/` into Mage AI
pipelines, starting with `gtms-dev-migration-legal-entity-related`. The workflows are
master-data migrations that read Google Sheets, transform/join, and upsert into a Postgres
(AWS RDS) `gtms` database.

## Source workflows (6 total, ~554 nodes)

| Workflow | Nodes |
|---|---|
| gtms-dev-migration-legal-entity-related (**first / template**) | 108 |
| gtms-dev-migration-counterparty-products | 167 |
| gtms-dev-migration-additional-charges | 96 |
| gtms-dev-migration-counterparty-location-related | 73 |
| gtms-dev-field-level-validation | 60 |
| gtms-dev-migration-linkages | 50 |

## What `legal-entity-related` does

- **Sources:** 9 tabs from the Google Sheet *"Jayson QL Master Data (Part 1) Compilation"*
  (`spreadsheetId 1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U`): Business Units, Countries,
  Addresses, States, Legal Entity, Profit Centers, Document Template, Document Content Snippet,
  Payment Term. Plus 5 DB Readers used as FK lookups.
- **Transforms:** GroupBy (×16), Joiner (×6), Rule Engine (×6), Column Renamer, String→Number,
  and `Table Row to Variable` / `Variable Expression` plumbing (collapses to plain pandas).
- **Targets (DB Merger upsert):** `master_countries`, `master_states`, `addresses`,
  `master_legal_entities`, `master_counterparties`, `master_business_units`,
  `master_document_templates`, `master_document_content_snippets`, `master_payment_terms`.
- **Tail:** appends row counts to a "Row Count Validator" sheet tab (QA audit log).

## Target database (from KNIME PostgreSQL Connector)

- Host: `gtms-dev-db.czo2260kqggm.ap-southeast-5.rds.amazonaws.com`
- Database: `gtms`, schema `public`, user `postgres`, auth USER_PWD, driver postgres 42.7.3.
- DB Merger semantics: upsert matched on **business key columns** (e.g. `master_business_units`
  on `(name, country)`), `id` is a DB-generated surrogate.

## Decisions (resolved via grilling)

| Topic | Decision |
|---|---|
| **Mage environment** | Local Mage project scaffolded in this repo, mounted into the existing `mageai/mageai:latest` Docker container. |
| **Granularity** | **One Mage pipeline per target table** (9 for legal-entity). |
| **Google Sheets access** | **Service-account JSON**; loader uses gspread/google-api to read tabs by name. |
| **Upsert mode** | **`INSERT … ON CONFLICT (business_keys) DO UPDATE`**. Verify/add unique index per table; per-table fallback to UPDATE-then-INSERT if a constraint can't exist. |
| **Run cadence** | **Repeatable / re-runnable**, manual trigger (no fixed schedule yet); idempotent. |
| **Orchestration** | **Parent `run_all` orchestrator pipeline** triggers children in FK-topological order; children still runnable alone. |
| **Block layout** | **Consolidated idiomatic blocks** (~3–4/pipeline): loader → transform(clean/rename/rule-engine) → transform(FK joins) → upsert exporter. |
| **Verification** | Dev-server-first, **trust + fix forward**. Row counts logged to Mage output. No formal parity harness. |
| **Validator write-back** | **Skipped for now** (log counts to Mage output instead). |
| **Multi-workflow scope** | **One Mage project**, build `legal-entity-related` end-to-end first as the reusable template, then port the other 5. |

## Mage project shape

```
/Users/skribble/Documents/mage-ai/
  metadata.yaml
  io_config.yaml            # gtms RDS connection; secrets via env
  mage_data/                # (gitignored runtime)
  utils/
    sheets.py               # service-account Google Sheets loader
    pg_upsert.py            # INSERT ... ON CONFLICT helper
  pipelines/
    legal_entity/
      load_master_countries/        # loader -> transform -> transform(FK) -> upsert
      load_master_states/
      load_addresses/
      load_master_payment_terms/
      load_master_document_content_snippets/
      load_master_document_templates/
      load_master_business_units/
      load_master_legal_entities/
      load_master_counterparties/
      run_all/                      # orchestrator, FK order
```

## FK run order (approximate — finalized from the join graph)

1. `master_countries` (root) — DONE (on_conflict on code)
2. `master_states` (→ country) — DONE (update_insert on name,country; FK filter on country)
3. `addresses` (→ country, state)
4. `master_payment_terms`, `master_document_content_snippets` (independent)
5. `master_document_templates` (→ content snippets)
6. `master_business_units` (→ country; Profit Centers feeds here — TBD)
7. `master_legal_entities` (→ address, country, business unit, payment terms)
8. `master_counterparties` (→ legal entities / address)

## Resolved at implementation time (by parsing `workflow.knime`, not user decisions)

- Exact per-table business keys for `ON CONFLICT`.
- Final FK topological order.
- Each table's rename maps, rule-engine expressions, groupby aggregations, type casts.
- Where the *Profit Centers* tab feeds.

## Open inputs needed from user

1. Path to the **Google service-account JSON** (sheet shared with its email).
2. **DB password** injection (env var name / Mage secret) and **target schema** for
   experimentation (same `gtms`/`public`, or a separate dev schema).
3. Go-ahead to scaffold, starting with `load_master_countries` as the first vertical slice.

## Build sequence

1. ✅ Scaffold Mage project (`gtms_migration/`, `io_config.yaml` wired to `.env`, shared utils) for Docker mount.
2. ✅ Build `le_load_master_countries` end-to-end (loader → clean → upsert) — **verified on dev DB**.
3. ✅ All 9 legal-entity pipelines built + verified on dev (countries, states, addresses,
   business_units, payment_terms, document_templates, document_content_snippets,
   legal_entities, counterparties[from Profit Centers]). FK-id resolution via
   `utils/blocks.resolve_fk` (name/address string -> surrogate id).
4. ✅ Orchestrator `le_run_all` (custom block, subprocess `mage run` per child in FK order);
   `mage run gtms_migration le_run_all` runs the whole workflow green.
5. ✅ Ran on dev — all green except states' expected `MH` non-existent-country finding.
6. 🔄 Replicate the pattern across the other workflows. Sequence (user): counterparty-products
   → counterparty-location-related → additional-charges → linkages (linkages last; depends on others).

## counterparty-products (prefix cpp_) — COMPLETE (all 11 + cpp_run_all orchestrator green)

Residual cleanup (needs DB DELETE auth): 24 duplicate master_specification_fips rows I created
before the int/float key fix (db=52, should be ~28). Logic now correct (passes, no new inserts).
Minor: master_specification_details shows 2 field mismatches (flagged, not blocking).

## STATUS: CONVERSION COMPLETE (2026-06-05)

All five migration workflows converted and green on dev:
- legal-entity (le_, 9 tables + le_run_all)
- counterparty-products (cpp_, 11 tables + cpp_run_all)
- counterparty-location-related (cpl_, 4 tables + cpl_run_all)
- additional-charges (ac_, 3 base tables + ac_run_all; the 3 inventory-location charge
  tables DEFERRED by user decision — "quite heavy"; specs documented below for later)
- linkages (lnk_, 4 junction tables + lnk_run_all; profit_centers resolved to
  master_counterparties id and JSON-wrapped in additional_costs)
The 6th KNIME workflow (field-level-validation) needs NO conversion — its function is built
into every pipeline's validate block (field-level + row-count + timestamps + FK checks,
written to the validator sheet tabs with mismatched_fields).

Open data findings (flagged by validation, source-side fixes):
- master_states: 'MH' state references a non-existent country (pre-existing, expected).
- Legal Entity x Tax: 'QL International Pte. Ltd' (tax PG(LC)STAX_EXEM) not in the Legal
  Entity sheet -> 1 link skipped.

## additional-charges (prefix ac_) — 3/6 base tables green (3 charge tables deferred)

6 targets. DONE/green: master_taxes (code), master_additional_cost_groups (code),
master_additional_costs (name; profit_centers JSON col EXCLUDED from write — sheet has a name
'QL FEED SDN. BHD.' but DB stores a json id array ['1'] under an unclear id-scheme; OPEN: confirm
what id profit_centers references, then resolve name->id and json-wrap. contract_types kept as JSON).
TODO (3 inventory-location charge tables, all need composite inventory_location_id resolution from
master_inventory_locations(code, legal_entity_id); 2 of them lack legal_entity_id in the sheet so
must resolve by code or name — fragile):
  - master_inventory_location_additional_charges WHERE(inventory_location_id, additional_cost_id) —
    resolve inv_loc (GTMS Inventory Location=code + legal_entity_id), additional_cost_id (name),
    tax_id (tax_code). Sheet 'Inventory Location Charges'. update_insert.
  - inventory_location_packaging_fees WHERE(inventory_location_id, packaging_product_id) — resolve
    inv_loc by name ('inventory location'; GTMS code blank), packaging_product_id (code). Sheet
    'Inventory Location Packing Charges'. update_insert.
  - inventory_location_storage_rates WHERE(sequence, duration_unit, inventory_location_id) — resolve
    inv_loc by code (GTMS Inventory Location), tax_id (tax_code/'SST'); int sequence. Sheet
    'Storage Charges'. update_insert.
Then ac_run_all orchestrator. Then the LINKAGES workflow (not started; 50 nodes; depends on all prior).

### Validator hardening this round (benefits all workflows)
- `_values_equal` now also matches: datetime-equal across formats ('2026-01-01 0:00:00' ==
  '2026-01-01 00:00:00') and JSON-equal (DB ['1'] == sheet '["1"]'). Plus `ci_cols` in upsert for
  case-insensitive key matching (functional lower(name) indexes), used by cpl_counterparties.

## counterparty-location-related (prefix cpl_) — COMPLETE (4/4 + cpl_run_all green)

master_counterparties: matched on (legal_entity_id, name) case-insensitively (new ci_cols option
in upsert; the 411 sheet rows already exist under different codes). `code` (M3 Code) intentionally
NOT written — the source M3 codes have 19 duplicates that would violate code_unique. OPEN: if the
user dedupes the source M3 codes, add `code` to the write so counterparties get re-coded.
Validator note: counterparties shows missing_in_db=1 — a name-case artifact of the case-sensitive
validate join vs the CI upsert (data is correct). cpp spec_details now PASSES (user combined the
duplicate India Rapeseed Meal / Moisture rows in the source).

## counterparty-location-related (prefix cpl_) — build details (done)

Targets: master_ports (code), master_counterparty_groups (name), master_inventory_locations
(code,legal_entity_id), master_counterparties (name,legal_entity_id). DONE/green: counterparty_groups,
ports (state/region name->id resolve), inventory_locations (legal_entity + port_code resolve).
TODO: master_counterparties — HARD: unique index is FUNCTIONAL `(legal_entity_id, lower(name))`
(generic ON CONFLICT can't target it; use update_insert with case-insensitive WHERE, or add
expression-conflict support), sourced from 'Counterparty v2' tab (many dedup/helper cols: name vs
cleaned_name, type->is_internal, M3 Code->code, legal_entity_id=LE name, profit center, etc).
Then a cpl_run_all orchestrator. Note this re-loads master_counterparties (503 rows) keyed on
(name, legal_entity_id) — distinct from the legal-entity workflow's Profit-Centers load (keyed on code).

### Validator enhancement (all workflows)
Field-level report now includes a `mismatched_fields` column naming exactly which fields differ
(+ 'missing timestamp'), per user request. Explained the cpp spec_details 2-mismatch: the sheet has
duplicate (group 156, spec 2) rows with conflicting `maximum`/`maximum_basis` — ambiguous source data,
now pinpointed in the Excel tab. cpp spec_fips 24 dup rows CLEANED (user-authorized, back to 28).

## counterparty-products (prefix cpp_) — build notes

11 targets. Sheet/merge-key/FK map known. Built via codegen (per-table spec -> 4 block files +
metadata). DONE (Batch A, verified): master_uoms, master_specifications, master_specification_groups,
master_traders, master_packing_units, master_products. TODO (Batch B, FK-id resolution):
master_specification_details (group+spec names->ids), master_specification_fips (composite
spec_detail_id), master_uom_conversions (product+2 uoms), master_lot_to_uom_conversions
(product+uom), master_price_indexes (uom + source_id_code->external_systems; some FK cols are
already ids in the sheet). Then a cpp_run_all orchestrator. Note: 'Price Index Product' tab has
no target merger -> skipped.

### Systemic fix (benefits all workflows)
- update_insert matching is now TRIM/text-insensitive (`TRIM(col::text)=value`) — source DB names
  carry trailing spaces; exact matching had created clean-named duplicate rows. Fixed in
  `utils/pg.upsert`. Cleaned up 7 spec + 5 spec_group dup rows I created (user-authorized DELETE,
  kept min-id original, only unreferenced rows). New helpers: `resolve_fk_composite`,
  `clean_df(float_cols=...)`, and on_conflict dedup-by-key in `export_table` (sheets have dup codes).

## legal-entity workflow: COMPLETE (2026-06-03)

Run order (= FK topological, in `custom/le_run_all.py`): countries → states → addresses →
business_units → payment_terms → document_templates → document_content_snippets →
legal_entities → counterparties. All verified; reports written to the `* Field Level
Validator` and `Row Count Validator` sheet tabs. New reusable utils:
`utils/blocks.py` (clean_df, resolve_fk, export_table), `utils/pg.py` (upsert w/ on_conflict +
update_insert modes, timestamp set-on-insert + COALESCE backfill), `utils/sheets.py`
(read + validator write-back), `utils/validate.py` (4 checks + FK existence, numeric/empty-aware).

## Validation findings on dev (2026-06-03)

- Comparison hardened (3 bugs fixed): missing-in-db no longer double-counts as field/
  ts mismatch; numeric-aware compare (120 == 120.0 from float upcast on nullable cols);
  empty-vs-NULL treated equal (`utils/validate._values_equal`).
- RESOLVED — **NULL created_at/updated_at on pre-existing rows** (addresses 2, payment_terms 48,
  states 2): upsert now backfills on UPDATE via COALESCE(col, now()) — fills nulls without
  churning existing values (`upsert(..., backfill_timestamps=[...])`, wired through export_table
  and the countries/states exporters). All matched rows now have timestamps; ts_missing=0.
- master_states: 'MH' row references a non-existent country (expected; matches the sheet's
  own Row Count Validator note).

## Status / proven setup (2026-06-03)

- Mage project lives at `gtms_migration/`; repo root mounts to `/home/src` in the
  `mageai/mageai:latest` container. Custom code imported as `from gtms_migration.utils...`.
- Run a pipeline headless:
  `docker run --rm --env-file .env -v "$PWD":/home/src -w /home/src mageai/mageai:latest mage run gtms_migration <pipeline_uuid>`
- Static check: `... python -m compileall -q /home/src/gtms_migration/...`
- Block naming convention: `le_*` prefix for legal-entity workflow (e.g. `le_clean_countries`).
- Per-table merge keys come from each KNIME DB Merger's `whereDataColumns` (conflict key)
  and `setDataColumns` (update columns). `master_countries`: conflict=`code`, update=`name,is_active`.
- Gotcha fixed: psycopg2 can't adapt numpy scalars — `utils/pg.upsert` coerces via `.item()`.
- Behavior note: upsert leaves `id` and timestamps untouched on conflict (matches DB Merger);
  DB-only rows not in the sheet are never deleted (sheet 239 vs table 242 countries).
- Validation baked into every pipeline (5th block, type `custom`, after the upsert):
  `utils/validate.validate_to_sheets(sheet_df, db_table, keys, check_name, field_tab)` runs
  three checks — row-count (every sheet row in DB), field-level (all fields match, per-row),
  timestamps (every DB row has created_at+updated_at) — writes the per-row report to the
  `<X> Field Level Validator` tab and this table's line in the shared `Row Count Validator` tab.
  Report layout mirrors KNIME: `<sheet cols>, id, <col> (Right)..., created_at, updated_at, field_level_validated`.
- Timestamps: exporter sets created_at/updated_at = now() **on insert only** (kept on conflict),
  via `utils/pg.upsert(..., set_timestamps_on_insert=['created_at','updated_at'])`. Required —
  the downstream system breaks on null timestamps.
- Sheets service account now has **Editor** access (needed for validator write-back); sheets util
  uses the full `spreadsheets` scope.
- Credentials: DB via `.env` `DB_*`; Sheets via service account
  `ais-gemini-key-98c2f3cc72b1451@945654130547.iam.gserviceaccount.com` (sheet shared, Viewer);
  `GOOGLE_APPLICATION_CREDENTIALS` + `GSHEET_ID` in `.env`.
