# Prod Data Extraction for Business Sign-off

## Goal
Extract everything migrated into **prod** into a **business-presentable** form so the
departments can compare it against the raw files they submitted and sign off the migration.

"Business-presentable" means:
- **No `id` columns at all** — drop surrogate PKs and every `*_id` foreign key.
- **All FKs resolved to a business-understandable code/name** (the same natural keys the
  pipelines resolved *from* on the way in — we simply reverse them).
- **Counterparties split into Customer form and Vendor form**, because the business gave
  them to us as two separate lists (Customer / Vendor), each keyed on its M3 code.

## Decisions (confirmed with user)
1. **Architecture:** one central, config-driven extractor (not a node per pipeline).
2. **Output:** a new dedicated Google Sheet, one tab per entity, tab names mirroring the
   raw dept-file tabs, business columns only.
3. **Scope:** business master + business junction tables. Exclude system/ACL
   (`users`, `roles`, `role_has_permissions`, `model_has_roles`, `user_contract_types`,
   `counterparty_users`, `permissions`) and seed-only ref tables.
4. **Counterparty split:** derive from `master_integration_references`
   (`customer_reference_no` → Customer + M3 code; `vendor_reference_no` → Vendor + M3 code);
   join back to `master_counterparties` (`integratable_id`) for the business attributes.

## Why central, not per-pipeline
The reverse-FK knowledge is already centralized: every `resolve_fk(...)` call in the
transformers is exactly the join we need to reverse, and `recon/validate_db.py` already holds
the table→business-key map and a working prod connection. One config table is ~40 entries and
one run; 56 per-pipeline nodes would duplicate the reverse-FK logic 56 times.

## Build: `recon/extract_signoff.py`
A single script mirroring the `recon/validate_db.py` / recon-engine pattern:
- Reads prod via `utils.pg.read_sql` (needs the SSM tunnel + `DB_HOST=host.docker.internal`,
  run headless in the mage docker image — same invocation as validate_db).
- Writes each entity to a **new spreadsheet** via a small `overwrite_tab(sheet_id, tab, df)`
  (reuse `utils/sheets.py`; create the target spreadsheet once, store its id in the script /
  env `EXTRACT_GSHEET_ID`).
- Driven by an `ENTITIES` config list. Each entry:
  ```
  {
    tab:        "Products",                 # output tab name (mirror raw)
    table:      "master_products",
    columns:    [ ("code","M3 Code"), ("description","Description"), ... ],  # db col -> business label, ordered
    fks:        [ ("packing_unit_id","master_packing_units","code","GTMS Packing Unit"),
                  ("default_uom_id","master_uoms","code","Default UoM") ],
    where:      None,                       # optional row scope
    order_by:   "code",
  }
  ```
- Engine per entity: `SELECT *` → for each fk, join ref table and replace the `*_id` with the
  resolved natural key under the business label → drop `id` and any leftover `*_id` →
  select/rename/reorder to `columns` → sort → write tab.
- Generic FK reverse = one helper: `read_sql('select id, <natural> from <ref>')`, map, assign.
  Composite/JSON cases handled explicitly (see below).

## Reverse-FK map (harvested from the transformers — source of truth)
Legal-entity group:
- `master_legal_entities`: business_unit_id→business_units.name, address_id→addresses.address,
  billing_address_id→addresses.address
- `master_counterparties` (profit centers, `code IS NOT NULL`) → **Profit Centers**:
  legal_entity_id→legal_entities.name, counterparty_group_id→counterparty_groups.name
- `addresses`, `master_business_units`, `master_countries`, `master_states`,
  `master_document_templates`, `master_payment_terms`: no/simple FKs
- `master_document_content_snippets`: document_template_id→document_templates.name

Products/specs group:
- `master_products`: packing_unit_id→packing_units.code, default_uom_id→uoms.code
- `master_specification_details`: specification_group_id→spec_groups.name, specification_id→specifications.name
- `master_specification_fips`: specification_group_id→spec_groups.name, specification_id→specifications.name
- `master_uom_conversions`: product_id→products.code, from_uom_id→uoms.code, to_uom_id→uoms.code
- `master_lot_to_uom_conversions`: product_id→products.code, uom_id→uoms.code
- `master_price_indexes`: source_id→external_systems.code, uom_id→uoms.code, basis_port_id→ports.code
- `master_specifications`, `master_specification_groups`, `master_packing_units`, `master_uoms`,
  `master_traders`: single business key, no FK

Counterparty/location group:
- `master_ports`: state_id→states.name, region_id→regions.name
- `master_inventory_locations`: legal_entity_id→legal_entities.name, port_id→ports.code
- `master_counterparty_groups`: name, no FK
- `master_counterparties` (cpl, `code IS NULL`) → see **Counterparty split**

Additional-costs group:
- `master_additional_costs`: additional_cost_group_id→additional_cost_groups.name;
  profit_centers is a **JSON array of ids** → map each id back to legal_entity/counterparty name
- `master_taxes`, `master_additional_cost_groups`: single key

Junctions (all ids reversed; present pure business keys):
- `counterparty_products`: counterparty_id→counterparties.name (code IS NOT NULL), product_id→products.code
- `product_contract_types`: product_id→products.code, contract_type_id→contract_types.code
- `product_specification_groups`: product_id→products.code, specification_group_id→spec_groups.name
- `master_price_index_products`: price_index_id→price_indexes.code, product_id→products.code
- `contract_term_products`: contract_term_id→contract_terms.name, product_id→products.code
- `contract_term_incoterms`: contract_term_id→contract_terms.name, incoterm_id→incoterms.code
- `legal_entity_taxes`: legal_entity_id→legal_entities.name, tax_id→taxes.code
- `legal_entity_contract_types`: legal_entity_id→legal_entities.name, contract_type_id→contract_types.code
- `payment_term_configs`: payment_term_id→payment_terms.name
- `payment_term_counterparties`: payment_term_id→payment_terms.name, counterparty_id→counterparties.name
- `inventory_location_packaging_fees`: inventory_location_id→inventory_locations.code, packaging_product_id→products.code
- `master_incoterms`, `master_contract_types`, `master_contract_terms`,
  `master_late_shipment_penalties`, `master_price_build_up_components`: single key

## Counterparty split (special-cased)
`master_counterparties` has **no** is_customer/is_vendor column — the split + M3 codes live in
`master_integration_references`:
- **Customer extract** = one row per integration_reference with `customer_reference_no` NOT NULL;
  M3 Code = `customer_reference_no`; business attributes joined from `master_counterparties`
  via `integratable_id`; FKs reversed (legal_entity_id→name, counterparty_group_id→name).
- **Vendor extract** = same, keyed on `vendor_reference_no`.
- Merged entities correctly appear in **both** (they have both ref numbers) — matching the
  raw Customer + Vendor tabs.
- Columns mirror the raw Customer / Vendor tabs (M3 Code, name, long_name, legal entity,
  group/type, reg no, tin, address, country, billing, phone, etc. — drop all ids).
- Also emit the merged `master_counterparties` view (Counterparty v2 shape) for completeness.

## Output layout
New Google Sheet "GTMS Prod Extract (Sign-off) — <date>". Tabs (mirroring raw dept files),
grouped: Legal Entity, Profit Centers, Business Units, Addresses, Countries, States, Payment
Term, Document Template, Document Content Snippet, Products, Packing Unit, UoM, Specifications,
SpecGroup, Spec Group Spec, SpecGroupFIP, Product UoM Conversion, Product Lot to UoM Conversion,
Price Index, Price Index Product, Trader, Contract Terms, Contract Type, Incoterm, Price Buildup
Component, Late Shipment Penalty, Ports, Inventory Locations, Counterparty Group,
**Customer**, **Vendor**, Counterparty (merged), Tax, Additional Cost Group, Additonal Costs,
+ business junctions (Profit Center x Product, Product x Contract Type, Spec Group x Product,
Contract Term x Product/Incoterm, Legal Entity x Tax/Contract Type, Payment Term Configs,
Payment Term x Profit Center, Inventory Location Packing Charges, Integration Reference).

## Execution phases
1. Build the config + engine skeleton; create the output spreadsheet; wire read/write.
2. Fill + run master tables (single-key, simple FK) — verify a few by eye.
3. Add junctions + composite/JSON cases (additional_costs.profit_centers, spec fips).
4. Add the Counterparty Customer/Vendor split from integration_references.
5. Full run against prod (tunnel up).
6. **Verify:** row count per tab vs `recon/validate_db.py` db counts; spot-check FK
   resolutions have zero unresolved (no blank where the id was non-null); confirm no `id`/`*_id`
   columns leaked into any tab.
7. Share the sheet link for dept sign-off.

## Risks / notes
- Needs the SSM prod tunnel up (`127.0.0.1:15432`) + docker `DB_HOST=host.docker.internal`.
- Verify column existence per table before finalizing labels (schema may have extra/renamed
  cols vs the transformer's written subset) — `SELECT *` then map is resilient.
- `master_states` country column: confirm whether it's a text/code or FK before labeling.
- Extract is **read-only** — no writes to prod, no writes to the Jayson working sheet.
