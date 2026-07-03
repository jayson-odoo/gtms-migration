"""legal-entity / run_all — orchestrator.

Runs every legal-entity pipeline in foreign-key dependency order. Each child runs as
its own `mage run` subprocess (a fresh process/event loop) for isolation and reliable
re-runs. Raises if any child fails so the orchestrator run is marked failed.
"""
import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

PROJECT = 'gtms_migration'

# FK topological order:
#   countries -> states/addresses/business_units; templates -> content_snippets;
#   business_units+addresses+countries -> legal_entities -> counterparties.
ORDER = [
    'le_load_master_countries',
    'le_load_master_states',
    'le_load_addresses',
    'le_load_master_business_units',
    'le_load_master_payment_terms',
    'le_load_master_document_templates',
    'le_load_master_document_content_snippets',
    'le_load_master_legal_entities',
    'le_load_master_counterparties',
]


@custom
def run_all(*args, **kwargs):
    results = {}
    for uuid in ORDER:
        print(f'\n=== running {uuid} ===', flush=True)
        r = subprocess.run(['mage', 'run', PROJECT, uuid], cwd='/home/src')
        results[uuid] = r.returncode
        print(f'=== {uuid} exit={r.returncode} ===', flush=True)

    failed = [u for u, rc in results.items() if rc != 0]
    print('\n=== run_all summary ===')
    for u in ORDER:
        print(f'  {"OK " if results[u] == 0 else "FAIL"} {u}')
    if failed:
        raise RuntimeError(f'run_all: {len(failed)} pipeline(s) failed: {failed}')
    return results
