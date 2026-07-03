# Master-Data Reconciliation — Lessons Learned (300626 recon + validation)

Durable notes from reconciling dept raw sheets ↔ the "Jayson QL Master Data" GSheet
(`1S0gHs6vQPAhpusycsqp-fQE9BPGrhg0rocZ9z-XHO3U`) and migrating to the GTMS Postgres (dev/prod).
All recon scripts live in `recon/`; backups in `recon/backup/`; audit trail in the sheet tab
`RECON 300626 - Applied`; validation report tabs `VALIDATION *`.

## 1. M3 code is NOT a global entity key — it is namespaced by side (Vendor vs Customer)
The SAME M3 code is a DIFFERENT entity on the vendor side vs the customer side. Real examples:
- `QBUNG001QF`: Vendor = `BUNGE S.A.`, Customer = `BUNGE AGRIBUSINESS`
- `QCARG001QF`: Vendor = `CARGILL FEED`, Customer = `CARGILL (MALAYSIA)`
- `QHENG001QF`: Vendor = `HENG SAY PROPERTIES`, Customer = `HENG LOONG FATT`

**Never match/overwrite/merge counterparties by M3 code alone.** Use `(M3 code + Vendor/Customer side)`
or the entity NAME. A "surgical overwrite by M3 code" silently conflates vendor-only entities that
share a code with a different customer (they get renamed to the customer twin and merged away).
Counterparty v2 disambiguates via the `M3 code + Vendor / Customer` column.

## 2. Counterparty v2 vendor/customer merge model
- Match a vendor ⇄ customer by NAME within a legal entity → ONE merged row: `Is Vendor=TRUE`,
  `Is Customer=TRUE`, `M3 Code` = customer code, `M3 Vendor Code (for merged vendor & customer)` = vendor code.
- Vendor-only / customer-only → its own row, `M3 Code` = that side's code, other flag blank.
- cpl transformer keeps rows where `Unique / Duplicate` ∈ {unique, duplicate} (duplicate M3 code is
  harmless: cpl does NOT write `code`, and the key is `(legal_entity_id, name)`).
- The DB has a functional unique index `(legal_entity_id, lower(name))` → same-name/different-code rows
  collapse to one (expected; not data loss — `missing_in_db=0`).

## 3. Products re-master — generic vs origin-specific
Raw Purchasing models products as GENERIC with origin as an ATTRIBUTE (`TGQMZ` MAIZE, origins
[ARG,BRAZIL]); Jayson had ORIGIN-SPECIFIC products (`TGQHMZA` argentina maize…). Decision: raw is master,
**origin lives in the SPEC GROUPS** (they carry origin in the name). Collapsed ~40 origin-specific → 39
generic, remapped ALL product junctions (counterparty_products, product_contract_types,
product_specification_groups, price_index_products, uom/lot conversions, contract_term_products,
inventory_location_packaging_fees). Then FK-ordered prod delete of the superseded old products + children.

## 4. SpecGroupFIP scope
Emit a FIP row ONLY when a spec has a MIXED allowance tier (both `1:1` and `2:1`). Single-band specs get
NO FIP row. In practice only HI-PRO SOYA BEAN MEAL **Protein** qualifies. The raw's ~363 FIP lines are
mostly single-band specs that are NOT FIP; Jayson's ~48 (soya protein 2-tier) is the correct scope.

## 5. Renaming a natural key cascades (payment terms, spec groups, counterparties)
Sheets key on a NAME (payment_terms.name, spec_groups.name, counterparties.(le,name)). Renaming in the
sheet + upsert INSERTS new-named rows while OLD-named rows REMAIN → duplicates. Cascade to fix:
1. propagate the new name to ALL dependent tabs that resolve by name (configs, x-product, FIP, etc.),
2. re-run those junction pipelines,
3. FK-ordered DELETE of the stale old-named parents + their orphaned junction rows on prod (backup first).
Also: dependent sheets that reference a renamed entity by name must be updated too, or junctions keep
resolving to the stale id (e.g. Payment Term Configs / Payment Term x Profit Center used old PT names).

## 6. Validator + util gotchas
- **Non-unique validation key** produces phantom field-mismatches: integration_references has merged
  vendor+customer rows sharing `integratable_id`, so the key must include `vendor_reference_no,
  customer_reference_no`. (162 phantom mismatches → 0 after fixing the key.)
- **`utils/sheets.py _df_to_values`** crashed on list/array cells (JSON-array column like `profit_centers`
  = `['1','2']`) — `pd.isna(list)` is ambiguous. Made it list/tuple/set/dict-safe.
- Headless `mage run` prints `RuntimeError: no running event loop` which MASKS the real psycopg2 error —
  always grep the log for `NotNullViolation` / `Violation` / `KeyError` / `does not exist`.
- **Exporter `update_cols` can only include a column the TRANSFORMER emits** — adding `reference_2` to the
  exporter alone → `KeyError: 'reference_2'`; must add it to the transformer `COLS`/`NULLABLE` too.
- **`document_content_snippets.document_template_id`** must be the template NAME (`SALES_CONTRACT`), not a
  numeric id — the transformer resolves it by name (`resolve_fk`). Numeric `5` → 0 rows migrate.
- NOT NULL DB column + blank sheet cell aborts the whole upsert batch → add col to `require_non_null` to
  skip+report, or backfill (e.g. `master_products.category` was NOT NULL and blank on rebuild).

## 7. Reading raw dept files
Raw dept sheets are **xlsx Office files in Drive** — read via Drive API `get_media` + openpyxl, NOT the
Sheets API (which 400s on Office files). Raw tabs are messy: instruction-row headers (`M3 max length: 3`),
hierarchical DRAFT blocks (SpecGroup/FIP: product row starts a block; origins/sellers/spec-lines are
independent vertical lists), banner rows (`QL FEED SDN BHD`), a./b. group sub-headers (Additional Charges),
prices in an unexpected column. Header row is not always row 0 (ACC Vendor/Customer = row 0; others vary).

## 8. Reconciliation methodology
- ADDITIVE-only (append missing by key) vs FIELD-LEVEL overwrite are different. Additive won't propagate
  raw field improvements (e.g. corrected names, spaced `billing_address`) into Jayson. When names/fields
  drift, do a field-level raw→Jayson overwrite — but key it correctly (see #1).
- Jayson is often CURATED BETTER than raw (payment-term full names, trader full names) — don't blindly
  overwrite Jayson with raw; make write-back selective.
- Country codes need ISO normalization: `SW`/`SZ` → `CH` (Switzerland), `VT` → `VN` (Vietnam).
- Additonal Costs = raw `Additional Charges` ∪ `Inventory Location Charges`; profit_centers can be MULTIPLE
  (transformer splits pipe/semicolon names → JSON id array, scoped `code IS NOT NULL`).

## 9. Operational
- Prod = AWS SSM port-forward on `127.0.0.1:15432` → container uses `host.docker.internal:15432`
  (`-e DB_HOST=host.docker.internal`). The tunnel DIES FREQUENTLY (listener up but session dead);
  restart: `pkill -f session-manager-plugin` then the `aws ssm start-session …` cmd. Sheets API is
  independent of the tunnel — sheet-only work continues when the DB is down.
- Every destructive prod op: dynamic FK-dependent discovery, CSV backup first, dry-run (safety-abort on
  implausible counts), then `GTMS_DELETE=1`. Repoint transactional refs (physical_contracts, voyages,
  billing_document_line_items) instead of deleting; delete junction rows (run_all regenerates them).
- Sheets API ~60 reads/min → cache reads + retry(429, sleep 25). Google Sheets tab col 0 may be `id` not
  the business key — index by column NAME, not position.
