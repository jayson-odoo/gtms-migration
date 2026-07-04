"""Top-level orchestrator — runs every per-workflow *_run_all in cross-workflow FK order.

Each child is itself an orchestrator (subprocess `mage run` per leaf pipeline), so this
nests one level: run_all -> <wf>_run_all -> the workflow's table pipelines. Click/run this
one pipeline to migrate everything.

Order: legal-entity masters first; linkages last (depend on the others); access-control
(acl) is independent and runs at the end.
"""
import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PROJECT = 'gtms_migration'
ORDER = [
    'le_run_all',   # countries, states, legal entities, addresses, ... (foundational)
    'cpl_run_all',  # counterparty-location: ports/locations (uses le masters only)
    'cpp_run_all',  # counterparty-products (price_indexes resolve basis_port -> master_ports)
    'ac_run_all',   # additional-charges
    'lnk_run_all',  # linkages / junctions (depend on all prior workflows)
    'acl_run_all',  # users, roles, role_has_permissions (independent)
]


@custom
def run_all(*args, **kwargs):
    results = {}
    for uuid in ORDER:
        print(f'\n########## running {uuid} ##########', flush=True)
        r = subprocess.run(['mage', 'run', PROJECT, uuid], cwd='/home/src')
        results[uuid] = r.returncode
        print(f'########## {uuid} exited {r.returncode} ##########', flush=True)

    print('\n=== run_all summary ===')
    for u in ORDER:
        print(f'  {"OK " if results[u] == 0 else "FAIL"} {u}')
    failed = [u for u, rc in results.items() if rc != 0]
    if failed:
        raise RuntimeError(f'run_all: {len(failed)} workflow(s) failed: {failed}')
    return results
