"""Platform-neutral CP4 release candidate validation; no publishing or API calls."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def call(*args:str,expected:int=0):
    env=os.environ.copy()
    env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+env.get('PYTHONPATH','')
    p=subprocess.run([sys.executable,*args],cwd=ROOT,env=env)
    if p.returncode!=expected:
        raise RuntimeError(f'Command failed: {args[0]} {args[1:4]}, got exit {p.returncode}, expected {expected}')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--project15-audit',type=Path,default=None,help='Optional real Project 15 CP4 audit export; read only')
    a=p.parse_args()
    base=Path('outputs/cp4_replay')
    base_cp1=base/'cp1_report.json'
    base_cp2=base/'cp2_report.json'
    call('-m','ai_reliability.cli','cp1','--output',str(base_cp1))
    call('-m','ai_reliability.cli','cp2','--baseline',str(base_cp1),'--output',str(base_cp2))
    for variant in ('reference','unsafe_allow','overblock','bad_citation','review_bypass'):
        output=base/f'cp3_{variant}'
        call('-m','ai_reliability.cli','cp3','--baseline',str(base_cp1),
             '--cp2-baseline',str(base_cp2),'--variant',variant,'--output-dir',str(output),
             expected=0 if variant=='reference' else 1)
        call('-m','ai_reliability.cli','cp3-verify','--output-dir',str(output))
        result=json.loads((ROOT/output/'cp3_report.json').read_text(encoding='utf-8'))
        expected='PASS' if variant=='reference' else 'BLOCK'
        if result['overall_development_gate']!=expected:
            raise RuntimeError(f'Unexpected candidate gate for {variant}')
    sample=ROOT/'data/fixtures/cp4_project15_audit_contract_sample.json'
    call('scripts/project15_bridge.py','--source',str(sample),
         '--output',str(base/'project15_contract_sample.json'))
    if a.project15_audit:
        source=a.project15_audit.expanduser().resolve()
        if not source.is_file():
            raise RuntimeError('Selected real Project 15 report does not exist')
        call('scripts/project15_bridge.py','--source',str(source),
             '--output',str(base/'project15_actual_readonly.json'))
    call('scripts/release_audit.py','--mode','candidate',
         '--output',str(base/'candidate_audit.json'))
    summary={
        'schema_version':'cp4.local.v1',
        'test_suite':'Run pytest separately and verify zero skips',
        'cp1':'PASS', 'cp2':'PASS', 'cp3_reference':'PASS',
        'cp3_deliberately_faulty_candidates_blocked':4,
        'cross_project_contract':'SYNTHETIC_SAMPLE_VALIDATED',
        'cross_project_real_report_supplied':bool(a.project15_audit),
        'release_audit_mode':'CANDIDATE_ONLY_NOT_STAGED_INDEX',
        'external_calls':0,
        'external_writes':0,
        'publication':'NOT_AUTHORIZED',
        'notes':['Real Git-index scan requires a staged index, separately approved',
                 'Hosted CI cannot be claimed until observed after approved publication',
                 'Synthetic fixtures and in-process load do not demonstrate production security/availability'],
    }
    (ROOT/base/'cp4_validation_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print('CP4 local replay succeeded: CP1 PASS, CP2 PASS, CP3 reference PASS, 4 negative candidates BLOCK, manifests verified; candidate path audit passed.')
    print('P15 bridge sample validated; REAL P15 source='+('YES' if a.project15_audit else 'NOT SUPPLIED'))
    print('Evidence: outputs/cp4_replay/cp4_validation_summary.json plus candidate_audit.json')
    print('This is NOT a GitHub CI run or production publication approval.')

if __name__=='__main__':
    try: main()
    except (OSError,ValueError,RuntimeError) as exc:
        print(f'CP4 failed: {type(exc).__name__}: {exc}',file=sys.stderr)
        raise SystemExit(1)
