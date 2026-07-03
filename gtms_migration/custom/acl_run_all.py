"""acl / run_all — orchestrator (subprocess per child, FK order).

roles must load before role_has_permissions (role_name -> roles.id resolution).
users is independent. permissions are assumed already present in the DB.
"""
import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PROJECT = 'gtms_migration'
ORDER = [
    'acl_load_users',
    'acl_load_roles',
    'acl_load_role_permissions',
    'lnk_load_counterparty_users',  # user->profit-center; needs users (above) + counterparties (cpl)
    'lnk_load_model_has_roles',     # user->role; needs users + roles
    'lnk_load_user_contract_types',  # user->contract type; needs users + master_contract_types (lnk)
]


@custom
def run_all(*args, **kwargs):
    results = {}
    for uuid in ORDER:
        print(f'\n=== running {uuid} ===', flush=True)
        r = subprocess.run(['mage', 'run', PROJECT, uuid], cwd='/home/src')
        results[uuid] = r.returncode
    print('\n=== acl run_all summary ===')
    for u in ORDER:
        print(f'  {"OK " if results[u] == 0 else "FAIL"} {u}')
    failed = [u for u, rc in results.items() if rc != 0]
    if failed:
        raise RuntimeError(f'acl_run_all: {len(failed)} failed: {failed}')
    return results
