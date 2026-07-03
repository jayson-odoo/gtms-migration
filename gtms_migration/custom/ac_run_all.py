"""additional-charges / run_all — orchestrator (base tables; inventory-location charge
tables intentionally deferred). Subprocess `mage run` per child in dependency order.
"""
import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PROJECT = 'gtms_migration'
ORDER = [
    'ac_load_master_taxes',
    'ac_load_master_additional_cost_groups',
    'ac_load_master_additional_costs',
]


@custom
def run_all(*args, **kwargs):
    results = {}
    for uuid in ORDER:
        print(f'\n=== running {uuid} ===', flush=True)
        r = subprocess.run(['mage', 'run', PROJECT, uuid], cwd='/home/src')
        results[uuid] = r.returncode
    print('\n=== ac run_all summary ===')
    for u in ORDER:
        print(f'  {"OK " if results[u] == 0 else "FAIL"} {u}')
    failed = [u for u, rc in results.items() if rc != 0]
    if failed:
        raise RuntimeError(f'ac_run_all: {len(failed)} failed: {failed}')
    return results
