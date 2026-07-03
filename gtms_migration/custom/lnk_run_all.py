"""linkages / run_all — orchestrator (subprocess per child)."""
import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PROJECT = 'gtms_migration'
ORDER = [
    # standalone masters first (referenced by the junctions below)
    'lnk_load_master_incoterms',
    'lnk_load_master_contract_types',
    'lnk_load_master_contract_terms',
    'lnk_load_master_late_shipment_penalties',
    'lnk_load_master_price_build_up_components',
    # junctions / dependent
    'lnk_load_legal_entity_taxes',
    'lnk_load_product_contract_types',
    'lnk_load_counterparty_products',
    'lnk_load_product_specification_groups',
    'lnk_load_payment_term_configs',
    'lnk_load_payment_term_counterparties',
    'lnk_load_price_index_products',
    'lnk_load_integration_references',
    'lnk_load_inventory_location_packaging_fees',
    'lnk_load_inventory_location_storage_rates',
    'lnk_load_contract_term_incoterms',
    'lnk_load_contract_term_products',
    'lnk_load_legal_entity_contract_types',
]


@custom
def run_all(*args, **kwargs):
    results = {}
    for uuid in ORDER:
        print(f'\n=== running {uuid} ===', flush=True)
        r = subprocess.run(['mage', 'run', PROJECT, uuid], cwd='/home/src')
        results[uuid] = r.returncode
    print('\n=== lnk run_all summary ===')
    for u in ORDER:
        print(f'  {"OK " if results[u]==0 else "FAIL"} {u}')
    failed = [u for u, rc in results.items() if rc != 0]
    if failed:
        raise RuntimeError(f'lnk_run_all: {len(failed)} failed: {failed}')
    return results
