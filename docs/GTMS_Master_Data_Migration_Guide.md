# GTMS Master Data Migration — Complete Handover Guide

> **Audience:** the engineer taking over this system. This document explains, end to end,
> how department-submitted raw data becomes the "Jayson" master sheet, how the Jayson sheet
> is migrated into the GTMS Postgres database via Mage AI, what every script/pipeline does,
> and how to set the whole thing up from scratch (Google service account, Mage locally, and
> the AWS tunnel).
>
> **Repo:** `/Users/skribble/Documents/mage-ai` (a scaffolded Mage AI project + reconciliation tooling).
> Last updated: 2026-07-02.

---

## Table of contents

1. [The big picture (30-second version)](#1-the-big-picture)
2. [Key resources & identifiers](#2-key-resources--identifiers)
3. [Stage 1 — Raw source → Jayson sheet (reconciliation)](#3-stage-1--raw-source--jayson-sheet-reconciliation)
4. [Stage 2 — Jayson sheet → Database (Mage AI migration)](#4-stage-2--jayson-sheet--database-mage-ai-migration)
5. [The mapping reference (sheet tab → table → key)](#5-the-mapping-reference)
    - [5.7 Jayson sheet tab dictionary (what every tab is)](#57-jayson-sheet-tab-dictionary-what-every-tab-is)
6. [Setup guide](#6-setup-guide)
    - [6.1 Google service account + sharing the sheet](#61-google-service-account--sharing-the-sheet)
    - [6.2 Local Mage AI setup (Docker)](#62-local-mage-ai-setup-docker)
    - [6.3 AWS SSM tunnel (dev & prod DB access)](#63-aws-ssm-tunnel-dev--prod-db-access)
    - [6.4 The `.env` file](#64-the-env-file)
7. [Operations runbook (how to actually run it)](#7-operations-runbook)
8. [Validation & QA](#8-validation--qa)
9. [Troubleshooting & hard-won gotchas](#9-troubleshooting--hard-won-gotchas)
10. [Glossary](#10-glossary)

---

## 1. The big picture

This project migrates **master data** (the reference/lookup data — legal entities, counterparties,
products, ports, spec groups, payment terms, users, roles, etc.) into the **GTMS** application's
Postgres database. There are two stages:

```
 ┌──────────────────────┐   Stage 1: RECONCILE       ┌───────────────────────┐   Stage 2: MIGRATE      ┌──────────────────┐
 │  RAW dept submissions │   (recon/*.py scripts,     │  "Jayson" Google Sheet │   (Mage AI pipelines,   │  GTMS Postgres    │
 │  (8 xlsx in a Drive   │──▶ read-only diff + curated ▶│  = single source of    │──▶ loader→clean→FK-join ▶│  (AWS RDS: dev &  │
 │   folder, per dept)   │   selective write-back)    │   truth, ~35 data tabs) │   →upsert→validate      │   prod)          │
 └──────────────────────┘                             └───────────────────────┘                          └──────────────────┘
```

- **Stage 1 (Reconciliation):** Departments (Account, Purchasing, Sales, Shipping) submit Excel
  files. These overlap and conflict. The `recon/` Python scripts compare each raw file against
  the Jayson sheet, surface discrepancies, and **selectively** update Jayson. The Jayson sheet is
  curated better than raw in many places, so write-back is deliberate, not a blind overwrite.
- **Stage 2 (Migration):** Mage AI pipelines read each Jayson tab, clean/type-cast it, resolve
  foreign keys (name → surrogate id), and **upsert** into Postgres. Every pipeline validates itself
  and writes a QA report back to the sheet.

The whole thing originated as a conversion of **6 KNIME workflows** (~554 nodes) into Mage AI
pipelines. That conversion is **complete**; all 35 target tables are populated on prod.

> **Mental model:** The Jayson sheet is the contract between "the business" and "the database."
> Departments negotiate the sheet (Stage 1); Mage deterministically pushes the sheet to the DB
> (Stage 2). If the DB is wrong, fix the sheet and re-run — the migration is idempotent (re-runnable).

---

## 2. Key resources & identifiers

| Thing | Value |
|---|---|
| **Repo root** | `/Users/skribble/Documents/mage-ai` |
| **Mage project name (UUID)** | `gtms_migration` |
| **Jayson source sheet** | "Jayson QL Master Data (Part 1) Compilation" — Google Sheet ID `1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U` (~122 tabs: data tabs + `* Field Level Validator` tabs + `RECON */VALIDATION *` report tabs + old/junk copies) |
| **Raw submissions Drive folder** | "300626 Master Data" — folder ID `1GeN2hKmsX1KOEJ9jCzDuG42BNFSPdvIh` (8 xlsx files, downloaded to `raw_master/300626/`) |
| **Google service account** | `ais-gemini-key-98c2f3cc72b1451@945654130547.iam.gserviceaccount.com` (key file `gen-lang-client-0473500312-692604319c2e.json` in repo root) |
| **Dev DB** | host `gtms-dev-db.czo2260kqggm.ap-southeast-5.rds.amazonaws.com`, db `gtms`, schema `public`, user `postgres` |
| **Prod DB** | `ql-gtms-rds-prod.c7muggg0s7ma.ap-southeast-5.rds.amazonaws.com`, db `gtms`, user `gtmsapp`, region `ap-southeast-5` |
| **Prod bastion (SSM target)** | EC2 instance `i-0d2a65aac559cbbb4` |
| **Docker image** | `mageai/mageai:latest` |
| **Mage UI** | `http://localhost:6789` (when the UI container is running) |

> ⚠️ **Secrets:** the DB password and the service-account private key are **not** in this doc.
> They live in `.env` and `gen-lang-client-*.json` respectively, both git-ignored. See §6.4.

---

## 3. Stage 1 — Raw source → Jayson sheet (reconciliation)

### 3.1 What the raw source is

Each department submits an `.xlsx` workbook to the Drive folder. As of the 300626 cycle there are
**8 files**, and they *overlap* — the same entity (e.g. "Payment Term") appears in several files with
different row counts because each dept owns a different slice:

| Raw file (by dept) | What it authoritatively owns |
|---|---|
| `Account QL Feed - Master Data (Part 1) …` | QLF side: Vendors, Customers, Legal Entity |
| `Account QL International - … (Part 1 …)` | QLI side: Legal Entity, Vendors, Customers |
| `Account … (Packing Unit, Trader, Payment Term, Payment Method)` | Packing Unit, Trader, Payment Method, Payment Term |
| `Purchasing … (Part 1) 20260629` | **Products (master)**, Spec Groups, Spec Group FIP, Additional Charges, Inv Loc Charges |
| `Purchasing … (Packing Unit Trader Payment Term) 20260629` | Packing Unit, Trader, Payment Term variants |
| `Sales QLI & QLF - GTMS_INVENTORY LOCATION_290626` | **Inventory Locations** (authoritative) |
| `Shipping QLI & QLF - Master Data Port` | **Ports** (authoritative), Warehouse Charges |
| `GTMS - User ID List` | Users / trader codes |

**Reading raw files (important):** these are Office `.xlsx` files in Drive. Read them with the
**Drive API `get_media` + openpyxl/pandas**, *not* the Sheets API (which 400s on Office files).
They are downloaded to `raw_master/300626/`.

> ⚠️ **Raw files go stale.** Departments keep editing them in Drive. Re-download from the folder
> (`1GeN2hKmsX1KOEJ9jCzDuG42BNFSPdvIh`) before validating, or you'll compare against an old copy.

**Raw data is messy:** instruction-row headers (e.g. "M3 max length: 3"), banner rows
(`QL FEED SDN BHD`), hierarchical *draft* blocks (Spec Group / FIP), sub-section headers
(`a. Shipping Agent Charges`), and the real header row is not always row 0.

### 3.2 What the Jayson sheet is

The Jayson sheet is the **single source of truth** consumed by the Mage pipelines. Every migration
loader reads a tab from this sheet. It is curated: names are cleaned, duplicates resolved, foreign
keys expressed as human-readable names.

### 3.3 The reconciliation engine (`recon/`)

All reconciliation scripts live in `recon/`. They are **standalone Python scripts** run inside the
Mage Docker image (so they share the same service-account + pandas/openpyxl environment). They read
the Jayson sheet via the Sheets API and the raw files via the Drive API.

The engine is **config-driven**: `recon/recon.py` holds a per-entity config list (`E = [...]`) where
each entry declares the raw file/tab, the Jayson tab, the business key, and the field-comparison rules
(`(raw_col, jayson_col, mode)` where mode is `exact`/`ci`/`num`/`pct`/`upper`). It classifies each row
as **ADDED** (in raw, absent in Jayson), **MISSING_IN_RAW** (informational), or **CHANGED**.

**The typical recon lifecycle per entity:**

1. **Diff** — `recon.py` (+ `classify.py`) produces `recon/out/{discrepancies,summary,changeplan}.csv`
   and writes review tabs to Jayson (`RECON 300626 - Summary / Details / ChangePlan / Candidates`).
2. **Human review** — a domain owner reviews the candidate tabs and marks rows to apply.
3. **Apply** — an `apply*.py` / `*_golive.py` / `*_add.py` script writes the **confirmed** cells to
   Jayson, always taking a CSV backup to `recon/backup/` first and logging to the `RECON 300626 - Applied` tab.
4. **Migrate** — re-run the relevant Mage pipeline(s) to push the sheet change to the DB (Stage 2).

**Script families in `recon/` (what handles what):**

| Prefix / script | Purpose |
|---|---|
| `recon.py`, `classify.py`, `apply.py`, `apply2.py` | Core generic diff → classify → apply engine |
| `validate_raw*.py`, `validate_db.py`, `validate_specs.py`, `validate_salescontract.py` | Validation: Jayson vs raw, and Jayson vs DB → `VALIDATION *` report tabs |
| `write_report.py`, `write_master_report.py` | Build the human-readable summary tabs (incl. `VALIDATION Raw-vs-Jayson MASTER`) |
| `cp_*.py`, `cpv2_*.py`, `cust_*.py` | Counterparty v2 reconcile: append missing, merge vendor/customer, name-drift fixes, country normalization, vendor-code fixes |
| `products_*.py`, `product_remap_plan.py`, `remap_A/BC/D_*.py`, `prod_delete_old_products.py` | Products re-master: collapse origin-specific → generic products, remap all product junctions, FK-ordered delete of superseded products on prod |
| `spec_*.py`, `sg_*.py`, `fip_*.py` | Spec Group / Spec Group Spec / SpecGroupFIP: candidate parsing, go-live, name standardization, DDGS grade fixes, stale cleanup |
| `pt_*.py` | Payment Term: trim to source, rename propagation, case-dedup, stale delete/repoint |
| `charges_*.py` | Additional Costs: delta vs live, blank-fills, apply |
| `sales_*.py`, `intref_*.py`, `invloc_*.py`, `ports_*.py` | Sales-contract snippets, integration references, inventory-location & ports recon |
| `quick_delta.py`, `spec_tally.py` | Lightweight per-entity delta / coverage tallies |
| `LESSONS_LEARNED.md` | **Read this.** Durable reconciliation lessons (see §3.4 highlights) |

### 3.4 Reconciliation lessons that will bite you (from `recon/LESSONS_LEARNED.md`)

1. **M3 code is NOT a global key — it is namespaced by side (Vendor vs Customer).** The same M3 code
   is a *different entity* on the vendor side vs the customer side (`QBUNG001QF` = "BUNGE S.A." as a
   vendor but "BUNGE AGRIBUSINESS" as a customer). Never match/merge counterparties by M3 code alone —
   use `(M3 code + Vendor/Customer side)` or the entity **name**.
2. **Jayson is often curated *better* than raw** (fuller payment-term names, fuller trader names).
   Write-back must be **selective**, not a blind raw→Jayson overwrite.
3. **Additive vs field-level are different operations.** Appending missing rows won't propagate raw
   *field* corrections into Jayson. If field values drifted, do a keyed field-level overwrite.
4. **Renaming a natural key cascades.** Sheets key on names (payment_terms.name, spec_groups.name,
   counterparties `(le, name)`). Renaming in the sheet + upsert *inserts* new-named rows while old ones
   remain → duplicates. The fix is: propagate the new name to every dependent tab, re-run those
   junction pipelines, then FK-ordered delete the stale old-named parents (backup first).
5. **Products model differs:** raw = generic product + origin-as-attribute; Jayson (old) = origin-specific.
   Decision taken: raw is master, **origin lives in the spec groups**. Products were collapsed to 39 generic.
6. **SpecGroupFIP scope:** only emit a FIP row when a spec has a *mixed* 1:1 / 2:1 allowance tier (in
   practice only HI-PRO SOYA BEAN MEAL Protein qualifies).

---

## 4. Stage 2 — Jayson sheet → Database (Mage AI migration)

### 4.1 What Mage AI is here

[Mage AI](https://www.mage.ai/) is an open-source data-pipeline tool. A **pipeline** is a DAG of
**blocks** (Python functions). We run it as the official Docker image `mageai/mageai:latest` with this
repo mounted at `/home/src`. The Mage project directory is `gtms_migration/`.

### 4.2 Project layout

```
gtms_migration/
  metadata.yaml            # Mage project config (project_uuid, spark/emr defaults — mostly unused)
  io_config.yaml           # Connection profiles; Postgres + Google creds read from .env via env_var()
  data_loaders/            # Block bodies: read a sheet tab                 (le_*, cpp_*, cpl_*, ac_*, lnk_*, acl_*)
  transformers/            # Block bodies: clean / type-cast / FK-resolve
  data_exporters/          # Block bodies: upsert into Postgres
  custom/                  # Validation blocks (*_validate_*.py) + orchestrators (*_run_all.py, run_all.py)
  pipelines/<uuid>/        # Each pipeline = a folder with metadata.yaml wiring blocks into a DAG
  utils/                   # Shared helpers (the heart of the system) — see §4.4
    sheets.py              #   read a tab; write validator tabs back
    pg.py                  #   the upsert engine (on_conflict / update_insert), prune
    blocks.py              #   clean_df, resolve_fk, resolve_fk_composite, export_table
    validate.py            #   row-count / field-level / timestamp checks -> report tabs
```

> **Note on the block files vs pipeline folders:** Mage stores block *code* under
> `data_loaders/`, `transformers/`, etc. (flat, keyed by block UUID), and stores the *DAG wiring*
> under `pipelines/<uuid>/metadata.yaml` (which block feeds which). A pipeline folder itself only
> contains `metadata.yaml`; the actual Python is in the type-named directories.

### 4.3 Anatomy of one pipeline (worked example: `le_load_master_countries`)

Every migration pipeline is the same 4-block chain:

```
data_loader  ──▶  transformer  ──▶  data_exporter  ──▶  custom (validate)
(read tab)        (clean/cast/FK)    (upsert to DB)       (compare & report)
```

**Block 1 — loader** (`data_loaders/le_load_countries_sheet.py`): reads the "Countries" tab as strings.

```python
from gtms_migration.utils.sheets import read_tab

@data_loader
def load_countries(**kwargs):
    return read_tab('Countries')
```

**Block 2 — transformer** (`transformers/le_clean_countries.py`): keep target columns, strip, cast
types, drop blank-key rows. (Simple tables inline this; most tables call `utils.blocks.clean_df`.)

**Block 3 — exporter** (`data_exporters/le_upsert_countries.py`): the actual write. Mirrors KNIME's
"DB Merger" — `INSERT ... ON CONFLICT (code) DO UPDATE SET name, is_active`.

```python
TABLE = 'master_countries'; CONFLICT_COLS = ['code']; UPDATE_COLS = ['name', 'is_active']

@data_exporter
def export_data(df, **kwargs):
    upsert(df, TABLE, conflict_cols=CONFLICT_COLS, update_cols=UPDATE_COLS,
           set_timestamps_on_insert=['created_at', 'updated_at'],
           backfill_timestamps=['created_at', 'updated_at'])
    return df   # pass cleaned rows to the validator
```

**Block 4 — validator** (`custom/le_validate_countries.py`): compares the cleaned sheet rows to the
DB table and writes two report tabs. See §8.

Tables that need FK resolution add a step in the transformer (or a second transformer) that calls
`resolve_fk` — e.g. legal_entities resolve `country` name → `master_countries.id`.

### 4.4 The shared utils (the engine — read these files)

**`utils/sheets.py`** — Google Sheets I/O via the service account (scope
`https://www.googleapis.com/auth/spreadsheets`, i.e. **read+write** — write is needed for validator tabs).
- `read_tab(tab_name)` → DataFrame (first row = header; **all cells returned as strings**; type
  coercion is the transformer's job). Normalizes ragged rows to header width (pads short, truncates
  over-wide — a stray unheadered column otherwise crashes the whole pipeline).
- `overwrite_tab(tab_name, df)` → clear + write (used to write report/staging tabs).
- `upsert_row_count_validator(...)` → maintain the shared `Row Count Validator` tab.

**`utils/pg.py`** — Postgres + the upsert engine.
- `get_connection()` reads `DB_*` from env.
- `upsert(df, table, conflict_cols, update_cols, mode=...)` — replicates KNIME's DB Merger. Two modes:
  - `on_conflict` — `INSERT ... ON CONFLICT (keys) DO UPDATE`. Fast/atomic; **requires a unique index**
    on the conflict cols. Empty SET (a pure junction) becomes `DO NOTHING`.
  - `update_insert` — per-row `UPDATE ... WHERE keys`; `INSERT` if nothing matched. No unique index
    needed. Key matching is **type-aware**: numeric keys compared numerically (`1 == 1.0`), text keys
    `TRIM`-ed, and `ci_cols` compared case-insensitively (for `LOWER(...)` functional unique indexes).
  - **`id` is dropped before insert** unless `id` *is* the conflict key — the sheet may carry ids that
    collide with an independently-seeded prod's PKs; letting the sequence assign ids avoids clashes.
  - Timestamps: `set_timestamps_on_insert` sets `now()` on INSERT; `backfill_timestamps` fills NULLs on
    UPDATE via `COALESCE(col, now())` without churning existing values.
- `prune_to_keys(table, conflict_cols, sheet_df, dry=...)` — opt-in "de-pollution": delete DB rows
  whose business key isn't in the sheet. FK-blocked / NULL-key rows are kept. Gated by env `GTMS_PRUNE`
  (`dry` = report only, `1` = delete).

**`utils/blocks.py`** — the per-table glue so each block stays short.
- `clean_df(df, cols, key_cols, int_cols=, bool_cols=, null_cols=, float_cols=)` — select/strip/cast,
  drop rows missing a business key.
- `resolve_fk(df, col, ref_table, ref_natural_col, where=None)` — replace a parent's *name* with its
  surrogate `id` (KNIME Joiner FK resolution). `where` scopes eligible parents (e.g.
  `'code IS NOT NULL'` to hit the profit-center row, not the same-named counterparty).
- `resolve_fk_composite(...)` — multi-column FK match (e.g. `spec_detail_id` from
  `(specification_group_id, specification_id)`).
- `export_table(...)` — the recommended exporter: applies `fk_filters` (skip rows whose FK value
  doesn't exist, so the insert can't violate an FK), `require_non_null` (skip+log rows null in a
  NOT-NULL column instead of aborting the batch), dedupes conflict keys, upserts, and optionally prunes.

**`utils/validate.py`** — see §8.

### 4.5 The six workflows and the orchestrators

The system is organized by **workflow prefix**, each a group of per-table pipelines plus a
`*_run_all` orchestrator. An orchestrator is a `custom` block that runs each child leaf pipeline as a
`subprocess` (`mage run gtms_migration <child>`) in FK-topological order and fails if any child fails.

| Prefix | Workflow | Orchestrator | Contents |
|---|---|---|---|
| `le_` | Legal-entity related | `le_run_all` | countries, states, addresses, business_units, payment_terms, document_templates, document_content_snippets, legal_entities, counterparties (profit centers) |
| `cpp_` | Counterparty-products | `cpp_run_all` | uoms, specifications, specification_groups, traders, packing_units, products, specification_details, specification_fips, uom_conversions, lot_to_uom_conversions, price_indexes |
| `cpl_` | Counterparty-location | `cpl_run_all` | counterparty_groups, ports, inventory_locations, counterparties (Counterparty v2) |
| `ac_` | Additional-charges | `ac_run_all` | taxes, additional_cost_groups, additional_costs |
| `lnk_` | Linkages (junctions) | `lnk_run_all` | ~20 junction/link tables (see §5) — run **last**, depend on all masters |
| `acl_` | Access control (users/roles) | `acl_run_all` | users, roles, role_has_permissions |

**Top-level orchestrator: `run_all`** (`custom/run_all.py`) runs the six in this order:

```
le_run_all → cpp_run_all → cpl_run_all → ac_run_all → lnk_run_all → acl_run_all
```

So `mage run gtms_migration run_all` migrates **everything** in dependency order.

> The 6th original KNIME workflow (field-level-validation) needed **no** conversion — validation is
> baked into every pipeline's 4th block.

---

## 5. The mapping reference

Every migration table below is upserted with the given **conflict key** (the business key the upsert
matches on) and **mode**. This is the authoritative "what maps where" table, extracted from the
exporters. FK columns are resolved from a name/code in the sheet to a surrogate `id` in the transformer.

### 5.1 `le_` — Legal-entity

| Sheet tab | Target table | Conflict key | Mode |
|---|---|---|---|
| Countries | `master_countries` | `code` | on_conflict |
| States | `master_states` | `name, country` | update_insert |
| Addresses | `addresses` | `address, city, postcode, state` | update_insert |
| Business Units | `master_business_units` | `id` | on_conflict |
| Payment Term | `master_payment_terms` | `name` | update_insert |
| Document Template | `master_document_templates` | `name` | on_conflict |
| Document Content Snippet | `master_document_content_snippets` | `document_template_id, name` | on_conflict |
| Legal Entity | `master_legal_entities` | `code` | on_conflict |
| Profit Centers | `master_counterparties` | `code` | on_conflict |

### 5.2 `cpp_` — Counterparty-products

| Sheet tab | Target table | Conflict key | Mode |
|---|---|---|---|
| UoM | `master_uoms` | `code` | on_conflict |
| (Specifications) | `master_specifications` | `name` | update_insert |
| SpecGroup | `master_specification_groups` | `name` | update_insert |
| Trader | `master_traders` | `code` | on_conflict |
| Packing Unit | `master_packing_units` | `code` | on_conflict |
| Products | `master_products` | `code` | on_conflict |
| Spec Group Spec | `master_specification_details` | `specification_group_id, specification_id` | update_insert |
| SpecGroupFIP | `master_specification_fips` | `specification_detail_id, fip` | update_insert |
| Product UoM Conversion | `master_uom_conversions` | `product_id, from_uom_id, to_uom_id` | update_insert |
| Product Lot to UoM Conversion | `master_lot_to_uom_conversions` | `product_id, uom_id` | update_insert |
| Price Index | `master_price_indexes` | `code` | on_conflict |

### 5.3 `cpl_` — Counterparty-location

| Sheet tab | Target table | Conflict key | Mode |
|---|---|---|---|
| Counterparty Group | `master_counterparty_groups` | `name` | on_conflict |
| Ports | `master_ports` | `code` | on_conflict |
| Inventory Locations | `master_inventory_locations` | `code, legal_entity_id` | on_conflict |
| Counterparty v2 | `master_counterparties` | `legal_entity_id, name` | update_insert (`ci_cols=['name']`) |

### 5.4 `ac_` — Additional-charges

| Sheet tab | Target table | Conflict key | Mode |
|---|---|---|---|
| Tax | `master_taxes` | `code` | on_conflict |
| Additional Cost Group | `master_additional_cost_groups` | `code` | on_conflict |
| Additonal Costs *(sic)* | `master_additional_costs` | `name` | update_insert |

### 5.5 `lnk_` — Linkages / junctions (run last)

| Sheet tab | Target table | Conflict key | Mode |
|---|---|---|---|
| Contract Terms | `master_contract_terms` | `name` | update_insert |
| Contract Type | `master_contract_types` | `code` | update_insert |
| Incoterm | `master_incoterms` | `code` | update_insert |
| Late Shipment Penalty | `master_late_shipment_penalties` | `lower_bound_days, upper_bound_days` | update_insert |
| Price Buildup Component | `master_price_build_up_components` | `code` | on_conflict |
| Integration Reference | `master_integration_references` | *(full-refresh: delete by `external_system_id` then insert)* | — |
| Contract Term x Incoterm | `contract_term_incoterms` | `contract_term_id, incoterm_id` | on_conflict |
| Contract Term x Product | `contract_term_products` | `contract_term_id, product_id` | on_conflict |
| Profit Center x Product | `counterparty_products` | `counterparty_id, product_id` | on_conflict |
| User x Profit Center | `counterparty_users` | `counterparty_id, user_id` | on_conflict |
| Inventory Location Packing Charges | `inventory_location_packaging_fees` | `inventory_location_id, packaging_product_id, lower_bound, upper_bound` | update_insert |
| Legal Entity x Contract Type | `legal_entity_contract_types` | `legal_entity_id, contract_type_id` | on_conflict |
| Legal Entity x Tax | `legal_entity_taxes` | `legal_entity_id, tax_id` | on_conflict |
| User Roles | `model_has_roles` | `role_id, model_id, model_type` | on_conflict (DO NOTHING) |
| Payment Term Configs | `payment_term_configs` | `payment_term_id, document_type` | on_conflict |
| Payment Term x Profit Center | `payment_term_counterparties` | `payment_term_id, counterparty_id` | update_insert |
| Price Index Product | `master_price_index_products` | `price_index_id, product_id` | on_conflict |
| Product x Contract Type | `product_contract_types` | `product_id, contract_type_id` | on_conflict |
| Spec Group x Product | `product_specification_groups` | `product_id, specification_group_id` | on_conflict |
| User Contract Type | `user_contract_types` | `user_id, contract_type_id` | on_conflict |

### 5.6 `acl_` — Access control

| Sheet tab | Target table | Conflict key | Mode |
|---|---|---|---|
| Users | `users` | `email` | on_conflict |
| Roles | `roles` | `name, guard_name` | on_conflict |
| Role Permission | `role_has_permissions` | `permission_id, role_id` | on_conflict |

> **Notes that matter:**
> - `master_counterparties` is fed by **two** pipelines: `le_upsert_profit_centers` (keyed on `code`,
>   the 2 profit centers QLF/QLI) and `cpl_upsert_counterparties` (keyed on `(legal_entity_id, name)`,
>   the ~420 external counterparties). It is in `NO_PRUNE_TABLES` so neither pipeline deletes the other's rows.
> - `roles`, `role_has_permissions` are also never pruned (app-seeded super-admin grants).
> - Junction FKs are resolved **by name/code** in the transformer — that's why renaming a master
>   cascades (see §3.4 #4).

### 5.7 Jayson sheet tab dictionary (what every tab is)

The Jayson sheet has ~140 tabs. They fall into **five kinds**. Only the first two kinds are read by
the migration; the rest are either dead, auto-generated, or working scratch.

#### (a) Live master-data tabs — each feeds one migration loader

These hold the actual reference data. "→ table" is the DB target (full key/mode in §5).

| Tab | What it holds | → table |
|---|---|---|
| **Business Units** | QL business units / operating divisions | `master_business_units` |
| **Countries** | Country list (code, name) | `master_countries` |
| **States** | States/provinces, each under a country | `master_states` |
| **Legal Entity** | The QL legal entities (QLF, QLI, …) — the top of the org tree | `master_legal_entities` |
| **Addresses** | Physical addresses referenced by legal entities/counterparties | `addresses` |
| **Profit Centers** | The 2 internal profit centers (QLF/QLI) as counterparties (keyed on `code`) | `master_counterparties` |
| **Tax** | Tax codes/rates (SST, exemptions, …) | `master_taxes` |
| **Counterparty Group** | Groupings of counterparties | `master_counterparty_groups` |
| **Counterparty v2** | **The** counterparty master — all external vendors/customers, merged vendor+customer model, `Unique/Duplicate`, `Is Vendor`/`Is Customer`, M3 codes | `master_counterparties` |
| **Ports** | Sea/discharge ports (GTMS port codes) | `master_ports` |
| **Inventory Locations** | Warehouses/inventory sites per legal entity | `master_inventory_locations` |
| **Additional Cost Group** | Groupings for additional costs/charges | `master_additional_cost_groups` |
| **Additonal Costs** *(sic — misspelling is the live tab)* | The charge catalogue (handling, storage, admin fees, …) | `master_additional_costs` |
| **UoM** | Units of measure | `master_uoms` |
| **Product UoM Conversion** | Per-product conversions between two UoMs (e.g. MT↔ST) | `master_uom_conversions` |
| **Product Lot to UoM Conversion** | Per-product lot→UoM conversion factor | `master_lot_to_uom_conversions` |
| **Products** | The product master (39 **generic** products; origin lives in spec groups) | `master_products` |
| **Specifications** | The library of spec attributes (Protein, Moisture, Fibre, …) | `master_specifications` |
| **SpecGroup** | Named spec groups (per product / origin / seller / region variant) | `master_specification_groups` |
| **Spec Group Spec** | The spec lines (min/max/basis) belonging to each spec group | `master_specification_details` |
| **SpecGroupFIP** | "Fixed-in-price" protein-band tiers (only HI-PRO SOYA Protein qualifies) | `master_specification_fips` |
| **Price Index** | Price index / futures curve definitions | `master_price_indexes` |
| **Payment Term** | Payment term definitions (30 rows, follows source) | `master_payment_terms` |
| **Price Buildup Component** | Components used to build up a price | `master_price_build_up_components` |
| **Packing Unit** | Packaging units (bags, totes, drums, containers) | `master_packing_units` |
| **Trader (Salesperson)** | Trader/salesperson master | `master_traders` |
| **Contract Terms** | Named contract-term templates | `master_contract_terms` |
| **Late Shipment Penalty** | Penalty tiers by days-late bounds | `master_late_shipment_penalties` |
| **Document Content Snippet** | Reusable clause/snippet text per document template | `master_document_content_snippets` |
| **Document Template** | Document templates (sales contract, etc.) | `master_document_templates` |
| **Incoterm** | Incoterms (FOB, CIF, …) | `master_incoterms` |
| **Contract Type** | Contract types (physical / non-trade) | `master_contract_types` |
| **Integration Reference** | M3↔GTMS external-system cross-reference codes | `master_integration_references` |
| **Users** | Application users (the sheet's `email` column is the key) | `users` |
| **Roles** | Application roles | `roles` |
| **Role Permission** | Which permissions each role has | `role_has_permissions` |

#### (b) Live junction / link tabs — `x` in the name means a many-to-many link

Each row links two masters (resolved by name/code → ids). All are loaded by `lnk_` pipelines (§5.5),
except the two noted **DEFERRED** ones which are **not** migrated.

| Tab | Links | → table |
|---|---|---|
| **Legal Entity x Tax** | legal entity ↔ tax | `legal_entity_taxes` |
| **Legal Entity x Contract Type** | legal entity ↔ contract type | `legal_entity_contract_types` |
| **Profit Center x Product** | profit center (counterparty) ↔ product | `counterparty_products` |
| **Product x Contract Type** | product ↔ contract type | `product_contract_types` |
| **Spec Group x Product** | product ↔ spec group | `product_specification_groups` |
| **Price Index Product** | price index ↔ product | `master_price_index_products` |
| **Payment Term x Profit Center** | payment term ↔ profit center | `payment_term_counterparties` |
| **Payment Term Configs** | payment term ↔ document type config (6 doc types) | `payment_term_configs` |
| **Contract Term x Incoterm** | contract term ↔ incoterm | `contract_term_incoterms` |
| **Contract Term x Product** | contract term ↔ product | `contract_term_products` |
| **User x Profit Center** | user ↔ profit center | `counterparty_users` |
| **User Contract Type** | user ↔ contract type | `user_contract_types` |
| **User Roles** | user ↔ role (polymorphic) | `model_has_roles` |
| **Inventory Location Packing Charges** | inv location ↔ packaging product (tiered fees) | `inventory_location_packaging_fees` |
| **Inventory Location Charges** | inv location ↔ additional charge — **DEFERRED, not migrated** | (`master_inventory_location_additional_charges`) |
| **Storage Charges** | inv location storage rates — **DEFERRED, not migrated** | (`inventory_location_storage_rates`) |

#### (c) Dead / superseded / pre-seeded tabs — present but **NOT** migrated

| Tab | Why it's not used |
|---|---|
| **Vendor**, **Customer**, **Counterparty** | Old counterparty tabs — **superseded by Counterparty v2**. Left for history. |
| **Ports (Old)** | Previous ports layout, replaced by **Ports**. |
| **Regions** | The DB `master_regions` is **pre-seeded** by the app — not migrated from the sheet. |
| **Permissions** | The `permissions` table is **app-seeded** — the sheet copy is reference only. |

#### (d) Working copies / scratch / non-data tabs

| Tab | What it is |
|---|---|
| **Change Log** | Human-maintained log of edits to the sheet. Not read by anything. |
| **Copy of Counterparty v2**, **Copy of Inventory Location Charges** | Manual backup copies. Ignore. |
| **Sheet32**, **Sheet26** | Stray auto-named tabs (scratch). Ignore. |
| **Spec Group x Product (Suggested)** | Recon **staging** — fuzzy suggestions awaiting review; not live. |

#### (e) Auto-generated tabs — written **by** the tooling, not read as input

- **`<Entity> Field Level Validator`** (≈50 tabs) — per-row field comparison reports written by each
  pipeline's validate block (§8). One per migrated table.
- **`Row Count Validator`** — the shared pass/justification summary, one line per check.
- **`RECON 300626 - *`** — Stage-1 reconciliation staging & audit tabs (Summary, Details, ChangePlan,
  Applied, and per-entity candidate/NEW/Remap tabs). See §3.3.
- **`VALIDATION *`** — Stage-1 validation reports: Jayson-vs-Raw, Jayson-vs-DB, SalesContract, and the
  roll-up `VALIDATION Raw-vs-Jayson MASTER`. See §8.

> **Rule of thumb:** if a tab name has "**x**", it's a junction; "**Field Level Validator**",
> "**RECON**", or "**VALIDATION**" → auto-generated (safe to ignore/regenerate); "**Copy of**",
> "**(Old)**", "**Suggested**", or a bare "**SheetNN**" → scratch/dead. Everything else in list (a)
> is live master data that a pipeline reads.

---

## 6. Setup guide

This section is the "from a fresh laptop" runbook.

### 6.1 Google service account + sharing the sheet

The pipelines authenticate to Google Sheets/Drive with a **service account** (a robot Google identity
with its own email and JSON key). You already have one:
`ais-gemini-key-98c2f3cc72b1451@945654130547.iam.gserviceaccount.com`, key file
`gen-lang-client-0473500312-692604319c2e.json` in the repo root.

**To reuse the existing account (normal case):** just make sure the key JSON is present in the repo
root and pointed to by `GOOGLE_APPLICATION_CREDENTIALS` in `.env` (see §6.4), and that the sheet is
shared with the service-account email (below).

**To create a new service account from scratch (if you must rotate it):**

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → pick/create a project.
2. **APIs & Services → Enable APIs**: enable **Google Sheets API** and **Google Drive API**.
3. **APIs & Services → Credentials → Create Credentials → Service account.** Name it, create.
4. Open the service account → **Keys → Add key → Create new key → JSON**. Download it. Put it in the
   repo root (git-ignored by the `gen-lang-client-*.json` / `*.json` rules) and update `.env`.
5. Copy the service account's **email** (looks like `…@….iam.gserviceaccount.com`).

**Sharing the Jayson sheet with the service account (required):**

1. Open the "Jayson QL Master Data (Part 1) Compilation" sheet in Google Sheets.
2. Click **Share**.
3. Paste the service-account **email**.
4. Grant **Editor** (not just Viewer). Editor is required because the pipelines **write back** the
   validator report tabs (`* Field Level Validator`, `Row Count Validator`) and the `RECON`/`VALIDATION`
   tabs. Uncheck "Notify people."
5. Click **Share/Send**.

**Sharing the raw Drive folder** (only needed for Stage 1 reconciliation): open the "300626 Master Data"
folder in Drive → Share → add the service-account email as **Viewer**. (The folder was 404 to the
service account until it was explicitly shared — the account only sees what's shared with it.)

> The service account has **no** access to anything by default. If a script gets a 404 on a sheet or
> file, the fix is almost always "share it with the service-account email."

### 6.2 Local Mage AI setup (Docker)

**Prerequisites:** Docker Desktop, and the AWS CLI + Session Manager plugin (for §6.3).

Everything runs from the official image with the repo mounted — **no `pip install`, no local Mage
install**. Always run from the repo root and use `"$PWD"` (an absolute path) for the mount.

**A) Pull the image**

```bash
docker pull mageai/mageai:latest
```

**B) Headless run of a single pipeline (the workhorse command)**

```bash
cd /Users/skribble/Documents/mage-ai
docker run --rm --env-file .env \
  -v "$PWD":/home/src -w /home/src \
  mageai/mageai:latest \
  mage run gtms_migration <pipeline_uuid>
```

Replace `<pipeline_uuid>` with any name from §5 (e.g. `le_load_master_countries`) or an orchestrator
(`le_run_all`, `run_all`).

**C) The Mage UI (optional, browse/click-run at http://localhost:6789)**

```bash
cd /Users/skribble/Documents/mage-ai
docker run -d --name mage-ui -p 6789:6789 \
  --env-file .env \
  -e MAGE_DATA_DIR=/home/src/mage_data \
  -v "$PWD":/home/src \
  mageai/mageai:latest \
  /app/run_app.sh mage start gtms_migration
```

> ⚠️ **A running container keeps its start-time `--env-file` snapshot.** Editing `.env` afterwards does
> **not** change a running container — you must recreate it. This is why the prod UI container is
> started with an explicit `-e DB_HOST=host.docker.internal` override (see §6.3 / §7).

**D) Static syntax check (no DB/sheet needed)**

```bash
docker run --rm -v "$PWD":/home/src -w /home/src mageai/mageai:latest \
  python -m compileall -q /home/src/gtms_migration
```

**Config files** (already set up, but so you understand them):
- `gtms_migration/metadata.yaml` — project config; `project_uuid` is set.
- `gtms_migration/io_config.yaml` — the `default` profile. Postgres and Google entries read from `.env`
  via `{{ env_var('...') }}`. The relevant lines:
  - `POSTGRES_HOST/PORT/DBNAME/USER/PASSWORD` ← `DB_HOST`/`DB_PORT`/`DB_DATABASE`/`DB_USERNAME`/`DB_PASSWORD`
  - `GOOGLE_SERVICE_ACC_KEY_FILEPATH` ← `GOOGLE_APPLICATION_CREDENTIALS`

  (In practice the code reads env vars directly via `utils/pg.py` and `utils/sheets.py`, so `io_config.yaml`
  is mostly there for Mage's built-in connectors.)

### 6.3 AWS SSM tunnel (dev & prod DB access)

The GTMS RDS databases are **not** publicly reachable. Access is via an **AWS Systems Manager (SSM)
port-forwarding session** through a bastion EC2 instance. This opens a local port that forwards to the
RDS host.

**Prerequisites (one-time):**
1. Install the AWS CLI v2.
2. Install the **Session Manager plugin**:
   `session-manager-plugin` (macOS: `brew install --cask session-manager-plugin` or the official pkg).
3. Configure AWS credentials with SSM + the right region (`ap-southeast-5`): `aws configure`
   (or SSO). You need permission to `ssm:StartSession` on the bastion instance.

**Start the PROD tunnel** (forwards local `127.0.0.1:15432` → prod RDS `:5432`):

```bash
aws ssm start-session \
  --target i-0d2a65aac559cbbb4 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["ql-gtms-rds-prod.c7muggg0s7ma.ap-southeast-5.rds.amazonaws.com"],"portNumber":["5432"],"localPortNumber":["15432"]}' \
  --region ap-southeast-5
```

Leave that session running in its own terminal. Now `127.0.0.1:15432` on your Mac reaches prod Postgres
(use it from DBeaver, `psql`, etc.).

**Restart when it dies** (it dies frequently — the listener stays up but the SSM session goes dead,
symptom: "server closed the connection unexpectedly"):

```bash
pkill -f session-manager-plugin      # kill the stale session
# then re-run the aws ssm start-session command above
```

**Dev tunnel:** the dev DB (`gtms-dev-db.czo2260kqggm.ap-southeast-5.rds.amazonaws.com`, user
`postgres`) is reached the same way (historically forwarded to local `:5432`). You need the dev DB
password to actually connect — that credential is **not** in the repo (`.env` currently holds prod).
Ask whoever owns the RDS.

**How the Docker container reaches the tunnel — the key trick:**

- The tunnel listens on the **Mac's loopback** `127.0.0.1:15432`.
- Inside a container, `localhost` is the *container itself*, not the Mac. So the container must use
  **`host.docker.internal`** (Docker Desktop's alias for the host) to reach the Mac's loopback.
- Therefore, to run against **prod**, override the host at run time:

```bash
docker run --rm --env-file .env \
  -e DB_HOST=host.docker.internal \
  -v "$PWD":/home/src -w /home/src \
  mageai/mageai:latest \
  mage run gtms_migration <uuid>
```

- The `.env` on disk keeps `DB_HOST=localhost` (so your Mac-side tools like DBeaver work directly).
  The container gets the `host.docker.internal` override via `-e`.

> ⚠️ **If the tunnel is down, all DB work fails but Sheets work is unaffected** (the Sheets/Drive APIs
> don't go through the tunnel). Stage 1 reconciliation (sheet-only) can continue when the DB is down.

### 6.4 The `.env` file

Repo root `.env` (git-ignored). Structure (values redacted):

```dotenv
DB_CONNECTION=pgsql
DB_HOST=localhost              # container overrides to host.docker.internal for prod (see §6.3)
DB_PORT=15432                  # local port the SSM tunnel listens on
DB_DATABASE=gtms
DB_USERNAME=gtmsapp            # prod user (dev = postgres)
DB_PASSWORD=********           # NEVER put this on a command line — classifier blocks it; read from env
# In-container path to the Google service-account JSON (repo mounts at /home/src)
GOOGLE_APPLICATION_CREDENTIALS=/home/src/gen-lang-client-0473500312-692604319c2e.json
# Source spreadsheet
GSHEET_ID=1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U
```

Notes:
- `GOOGLE_APPLICATION_CREDENTIALS` is the **in-container** path (`/home/src/...`), because the repo is
  mounted at `/home/src`.
- To point at **dev** instead of prod: set `DB_HOST`/`DB_PORT`/`DB_USERNAME`/`DB_PASSWORD` to the dev
  values (and start the dev tunnel).
- The service-account key file and `.env` are both excluded by `.gitignore`.

---

## 7. Operations runbook

### 7.1 Run one table (dev)

```bash
cd /Users/skribble/Documents/mage-ai       # (.env points at dev; dev tunnel up)
docker run --rm --env-file .env -v "$PWD":/home/src -w /home/src \
  mageai/mageai:latest mage run gtms_migration cpp_load_master_products
```

### 7.2 Run everything (prod) — the standard migration

1. Start the prod SSM tunnel (§6.3) and confirm `127.0.0.1:15432` connects.
2. Run headless with the host override (does **not** touch the UI container):

```bash
cd /Users/skribble/Documents/mage-ai
docker run --rm --env-file .env -e DB_HOST=host.docker.internal \
  -v "$PWD":/home/src -w /home/src \
  mageai/mageai:latest mage run gtms_migration run_all 2>&1 | tee scratchpad/run_all.log
```

3. Read the tail summary (`OK`/`FAIL` per workflow). If a child failed, open its log at
   `mage_data/gtms_migration/pipelines/<child>/.logs/<run>/…log` — the orchestrator only prints `FAIL <child>`.

### 7.3 Run via the UI

The `mage-ui` container was recreated to target **prod** (started with `-e DB_HOST=host.docker.internal`),
so clicking **Run** in the UI writes to prod. If you need it to target dev, recreate the container
without that override. Remember: the container's env is frozen at start time — recreate to change it.

### 7.4 Pruning (optional de-pollution)

To delete DB rows not present in the sheet, set `GTMS_PRUNE`:
- `GTMS_PRUNE=dry` — report what *would* be deleted.
- `GTMS_PRUNE=1` — actually delete (FK-blocked and NULL-key rows are kept).

```bash
docker run --rm --env-file .env -e DB_HOST=host.docker.internal -e GTMS_PRUNE=dry \
  -v "$PWD":/home/src -w /home/src mageai/mageai:latest mage run gtms_migration run_all
```

`NO_PRUNE_TABLES = {master_counterparties, roles, role_has_permissions}` are never pruned.
**Caveat:** `run_all` prunes parents-before-children, so interlinked clusters may need a child-first
manual delete or a second pass; dry mode over-counts because it can't see FK blocks.

### 7.5 Destructive prod operations (deletes / re-masters)

Follow the pattern the `recon/` delete scripts use (e.g. `prod_delete_old_products.py`,
`*_stale_cleanup.py`):
1. **Dynamic FK discovery** — find all child tables referencing the target before deleting.
2. **CSV backup first** → `recon/backup/` (and `recon/backup/prod_delete/`).
3. **Dry-run** with a safety-abort on implausible counts.
4. Only then `GTMS_DELETE=1`.
5. **Repoint** transactional references (physical_contracts, voyages, billing_document_line_items)
   rather than deleting them; **delete** junction rows (run_all regenerates them).

> ⚠️ **Never put the prod password on a command line** — the safety classifier blocks it. Read `DB_*`
> from the environment inside scripts instead.

---

## 8. Validation & QA

Validation is built into **every** pipeline as the 4th block (`custom/*_validate_*.py`), calling
`utils/validate.validate_to_sheets(sheet_df, db_table, keys, check_name, field_tab)`. It runs three checks:

1. **Row count** — is every sheet row present in the DB table?
2. **Field level** — for each sheet row, do all fields match the DB row?
3. **Timestamps** — does every DB row have `created_at` and `updated_at`?

**Comparison is format-tolerant** (`_values_equal`): empty-vs-NULL equal; numeric equal
(`120 == 120.0`); datetime equal across formats; JSON equal (DB `['1']` == sheet `'["1"]'`).

**Outputs (written back to the Jayson sheet):**
- `<Entity> Field Level Validator` tab — per-row field comparison with a `mismatched_fields` column
  naming exactly which fields differ, plus a `checked_at` stamp (Asia/Kuala_Lumpur, UTC+8).
- Shared `Row Count Validator` tab — one line per **check** (matched on the unique `check_name` in
  column A, *not* the table name, because one table can have two checks — e.g. `master_counterparties`
  has `is_profit_centers_passed` and `is_counterparty_v2_passed`).

**Reading the validator:**
- `row count valid = false` is only a real problem when there is `missing_in_db > 0`, a field mismatch,
  a missing timestamp, or a bad FK. A DB count *greater* than the sheet (a superset — e.g. pre-seeded
  SYSTEM users) is informational, not a failure.
- Independent whole-sheet vs whole-DB reconciliation reports are produced by `recon/validate_db.py`
  (Jayson vs DB) and `recon/validate_raw*.py` (Jayson vs raw), landing in `VALIDATION *` tabs. The
  master summary lives in `VALIDATION Raw-vs-Jayson MASTER`.

---

## 9. Troubleshooting & hard-won gotchas

| Symptom | Cause / fix |
|---|---|
| **`RuntimeError: no running event loop`** in a headless run | Mage framework **noise** that *masks* the real error. Always capture full output and grep for the real psycopg2 exception: `NotNullViolation`, `…Violation`, `StringDataRightTruncation`, `KeyError`, `does not exist`. |
| **404 on a sheet or Drive file** | The service account isn't shared on it. Share the sheet/folder with the service-account email (§6.1). |
| **"server closed the connection unexpectedly" / DB timeouts** | The SSM tunnel died. `pkill -f session-manager-plugin`, then restart it (§6.3). |
| **DB writes go nowhere / wrong DB** | Container is using its frozen start-time env. For prod, pass `-e DB_HOST=host.docker.internal`; recreate the UI container to change its target. |
| **`KeyError: ['id'] not in index`** in a transformer | The source sheet dropped its `id` column but the transformer's `cols`/`int_cols` still list `id`. Drop `id` there. (DB assigns ids via the id-drop in `upsert`.) Watch `business_units`, which merges on `id`. |
| **`KeyError: '<col>'`** from an exporter | An `update_col` references a column the **transformer doesn't emit**. Add it to the transformer's `COLS`/`NULLABLE` too, not just the exporter. |
| **Whole upsert batch aborts on `NotNullViolation`** | A NOT-NULL DB column has a blank sheet cell. Add that column to `require_non_null` (skip+report) or backfill a default. All-NULL-key seed rows can't be pruned — delete them by `id`. |
| **Row count "SHORT" (db < sheet)** but `missing_in_db = 0` | Not data loss — **duplicate business keys** in the sheet collapse on upsert. Dedupe the source tab. |
| **Duplicate rows appear after a rename** | Renaming a natural key inserts new-named rows while old ones remain. Do the full rename cascade (§3.4 #4). |
| **Phantom field mismatches in the validator** | The validation key is non-unique (e.g. integration_references merged rows share `integratable_id`). Add more columns to the validator key. |
| **`document_content_snippets` rows don't migrate** | `document_template_id` must be the template **name** (`SALES_CONTRACT`), not a numeric id — the transformer resolves it by name. |
| **Sheets API 429 / rate limit** | ~60 reads/min. Cache reads and retry with `sleep 25`. |
| **Docker service-account key 404 despite being present** | The mount used a relative path and `cd` drifted `$PWD`. Always mount the **absolute** repo path. |
| **openpyxl/numpy import breaks** | Don't name a script `struct.py`/`_struct.py` — it shadows the stdlib `struct`. |

---

## 10. Glossary

- **Jayson sheet** — "Jayson QL Master Data (Part 1) Compilation" Google Sheet; the single source of
  truth for the migration. (Named after the previous owner.)
- **Raw / dept submissions** — the per-department `.xlsx` files in the "300626 Master Data" Drive folder.
- **Reconciliation (Stage 1)** — comparing raw against Jayson and selectively updating Jayson
  (`recon/` scripts).
- **Migration (Stage 2)** — pushing Jayson tabs into Postgres via Mage pipelines.
- **Pipeline** — a Mage DAG of 4 blocks (loader → transformer → exporter → validator) for one table.
- **Block** — a single Python function in a pipeline (a data_loader / transformer / data_exporter / custom).
- **Orchestrator (`*_run_all`)** — a `custom` block that `subprocess`-runs child pipelines in FK order.
- **Upsert** — insert-or-update keyed on a business key (mirrors KNIME's "DB Merger"). Two modes:
  `on_conflict` (needs a unique index) and `update_insert` (no index needed).
- **Conflict key / business key** — the natural key the upsert matches on (e.g. `code`, `name`,
  `(legal_entity_id, name)`).
- **FK resolution** — replacing a parent's human-readable name/code in the sheet with the parent's
  surrogate `id` from the DB (`resolve_fk`).
- **M3 code** — the code from the legacy M3 system; **namespaced by vendor/customer side** (see §3.4 #1).
- **SSM tunnel** — the AWS Session Manager port-forward that exposes the private RDS on a local port.
- **`host.docker.internal`** — Docker Desktop's alias letting a container reach the Mac host's loopback
  (where the tunnel listens).
- **Prune / `GTMS_PRUNE`** — opt-in deletion of DB rows not present in the sheet.
- **KNIME** — the visual ETL tool the original 6 workflows were built in, before conversion to Mage.

---

### Appendix — the two persistent knowledge files

Two long-form notes captured the day-to-day history and decisions during this project (in the AI
assistant's memory store, kept alongside the repo):
- **`knime-to-mage-project`** — the Stage 2 build history (pipeline-by-pipeline, prod cutover, utils hardening).
- **`master-data-reconciliation-300626`** — the Stage 1 reconciliation history (per-entity decisions).

They are dense but are the definitive record of *why* specific choices were made. Skim `recon/LESSONS_LEARNED.md`
first (it's the distilled version), then reach for those if you need the blow-by-blow.
```
