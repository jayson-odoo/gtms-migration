"""counterparty-location / run_all — orchestrator (FK order, subprocess per child)."""
import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PROJECT = 'gtms_migration'
ORDER = [
    'cpl_load_master_counterparty_groups',
    'cpl_load_master_ports',
    'cpl_load_master_inventory_locations',
    'cpl_load_master_counterparties',
]


@custom
def run_all(*args, **kwargs):
    results = {}
    for uuid in ORDER:
        print(f'\n=== running {uuid} ===', flush=True)
        r = subprocess.run(['mage', 'run', PROJECT, uuid], cwd='/home/src')
        results[uuid] = r.returncode
    print('\n=== cpl run_all summary ===')
    for u in ORDER:
        print(f'  {"OK " if results[u] == 0 else "FAIL"} {u}')
    failed = [u for u, rc in results.items() if rc != 0]
    if failed:
        raise RuntimeError(f'cpl_run_all: {len(failed)} failed: {failed}')
    return results
