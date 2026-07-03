"""counterparty-products / run_all — orchestrator (FK order, subprocess per child)."""
import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PROJECT = 'gtms_migration'
ORDER = [
    'lnk_load_master_incoterms',
    'cpp_load_master_uoms',
    'cpp_load_master_packing_units',
    'cpp_load_master_specifications',
    'cpp_load_master_specification_groups',
    'cpp_load_master_traders',
    'cpp_load_master_products',
    'cpp_load_master_specification_details',
    'cpp_load_master_uom_conversions',
    'cpp_load_master_lot_to_uom_conversions',
    'cpp_load_master_price_indexes',
    'cpp_load_master_specification_fips',
]


@custom
def run_all(*args, **kwargs):
    results = {}
    for uuid in ORDER:
        print(f'\n=== running {uuid} ===', flush=True)
        r = subprocess.run(['mage', 'run', PROJECT, uuid], cwd='/home/src')
        results[uuid] = r.returncode
    print('\n=== cpp run_all summary ===')
    for u in ORDER:
        print(f'  {"OK " if results[u]==0 else "FAIL"} {u}')
    failed = [u for u, rc in results.items() if rc != 0]
    if failed:
        raise RuntimeError(f'cpp_run_all: {len(failed)} failed: {failed}')
    return results
