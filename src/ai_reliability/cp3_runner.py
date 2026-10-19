"""CP3 offline security/failure suite with trace metadata and report integrity.

No hosted LLMs, network requests, or consequential writes. Every PASS is a
synthetic-evaluator development PASS, never a real deployment authorization.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any
from .cp1_runner import load_suite, evaluate
from .cp2_runner import SimulatedCandidate, _load_checked_json, run_cp2, score, VARIANTS
from .cp2_contract import GatePolicy
from .cp3_contract import OperationalPolicy, OperationalSuite
from .cp3_operations import run_operations, run_local_benchmark, run_local_thread_load
from .cp3_telemetry import local_tracing, sanitized_spans

FILES=('cp3_report.json','cp3_events.jsonl','cp3_spans.jsonl','cp3_dashboard.csv')


def _json(obj: Any) -> str:
    return json.dumps(obj,sort_keys=True,ensure_ascii=True,indent=2)+'\n'


def _write(path:Path,data:str)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(data,encoding='utf-8',newline='\n')


def verify_artifacts(directory:Path)->dict[str,Any]:
    """Check the fixed local manifest against report, event, and CSV bytes.

    A checksum manifest is not a digital signature; someone with write access to
    both the payload and manifest can replace them. Symlinks are denied here.
    """
    manifest_path=directory/'cp3_manifest.json'
    if directory.is_symlink() or manifest_path.is_symlink():
        raise ValueError('Symlinked output directory or manifest not accepted')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema_version')!='1.0' or manifest.get('filenames')!=list(FILES):
        raise ValueError('Manifest schema or filenames mismatch')
    if set(manifest.get('sha256',{}))!=set(FILES):
        raise ValueError('Manifest must cover exactly the four expected artifacts')
    for name in FILES:
        path=directory/name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing or symlinked artifact: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sha256'][name]:
            raise ValueError(f'Artifact integrity mismatch: {name}')
    report=json.loads((directory/'cp3_report.json').read_text(encoding='utf-8'))
    if report['schema_version']!='3.0' or report['overall_development_gate'] not in ('PASS','BLOCK'):
        raise ValueError('CP3 report schema invalid')
    events=[]
    for line in (directory/'cp3_events.jsonl').read_text(encoding='utf-8').splitlines():
        if line.strip():
            event=json.loads(line)
            if set(event) - {'schema_version','event_type','trace_id','case_id','attempt','fault_kind',
                             'modeled_latency_ms','timing_source','outcome','status','attempts','side_effect_count'}:
                raise ValueError('Unexpected trace keys (possible unsafe logging)')
            events.append(event)
    if len(events)!=report['observability']['structured_event_count']:
        raise ValueError('Event count does not reconcile to the report')
    spans=[json.loads(line) for line in (directory/'cp3_spans.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(spans)!=report['observability']['otel_span_count']:
        raise ValueError('OpenTelemetry span count does not reconcile')
    for span in spans:
        if set(span['attributes'])-{'case_id','event_type','fault_kind','observed_status','modeled_latency_ms','attempt'}:
            raise ValueError('Unsafe OpenTelemetry attributes present')
        if span['network_exported'] is not False:
            raise ValueError('Unexpected network tracing export')
    with (directory/'cp3_dashboard.csv').open(encoding='utf-8',newline='') as handle:
        rows=list(csv.DictReader(handle))
    if len(rows)!=report['observability']['dashboard_row_count']:
        raise ValueError('Dashboard row count does not reconcile')
    if len({row['case_id'] for row in rows})!=len(rows):
        raise ValueError('Duplicate dashboard case IDs')
    return {'verified':True,'artifact_count':len(FILES),'event_count':len(events),'dashboard_rows':len(rows),
            'status':report['overall_development_gate'],
            'integrity_type':'UNSIGNED_SHA256_LOCAL_TAMPER_CHECK'}


def run_cp3(*, cp1_fixture:Path,cp2_fixture:Path,cp3_fixture:Path,
            cp1_baseline:Path,cp2_baseline:Path,
            cp2_policy:Path,cp2_governance:Path,cp3_policy:Path,
            operational_fixture:Path,operational_policy:Path,
            output_dir:Path, variant:str='reference')->dict[str,Any]:
    if variant not in VARIANTS:
        raise ValueError('Unknown local candidate variant')
    if output_dir.is_symlink():
        raise ValueError('Symlinked output directory denied')
    # Provenance: both earlier user-verified reports must still match fresh
    # local deterministic replays. CP2 itself validates the CP1 report.
    cp2_replay=run_cp2(fixture=cp2_fixture,cp1_fixture=cp1_fixture,
                        baseline_path=cp1_baseline,policy_path=cp2_policy,
                        governance_path=cp2_governance,output=None,variant='reference')
    cp2_record=json.loads(cp2_baseline.read_text(encoding='utf-8'))
    if cp2_record!=cp2_replay or cp2_replay['comparison']['status']!='PASS':
        raise ValueError('CP2 baseline mismatch: restore the validated CP2 output')
    suite,suite_sha=load_suite(cp3_fixture)
    if suite.suite_id!='cp3_separate_locked_dev_2026_10':
        raise ValueError('Wrong frozen CP3 scenario version')
    prior_suite,_=load_suite(cp2_fixture)
    if suite.target_id != prior_suite.target_id:
        raise ValueError('CP3 target ID differs from CP2')
    if {c.case_id for c in suite.cases} & {c.case_id for c in prior_suite.cases}:
        raise ValueError('CP3 security suite must be distinct from CP2 development cases')
    policy_data,policy_sha=_load_checked_json(cp3_policy)
    policy=GatePolicy.model_validate(policy_data)
    if policy.policy_id!='cp3_locked_development_gate_v1':
        raise ValueError('Unexpected CP3 policy ID')
    reference=evaluate(suite,suite_sha)
    if reference['failed_count']:
        raise ValueError('CP3 locked oracle mismatch with reference adapter')
    candidate=evaluate(suite,suite_sha,SimulatedCandidate(variant))
    comparison=score(reference,candidate,policy)

    ops_data,ops_sha=_load_checked_json(operational_fixture)
    ops_suite=OperationalSuite.model_validate(ops_data)
    ops_policy_data,ops_policy_sha=_load_checked_json(operational_policy)
    ops_policy=OperationalPolicy.model_validate(ops_policy_data)
    with local_tracing() as (tracer, exporter):
        with tracer.start_as_current_span('cp3.offline_fault_injection'):
            ops_report,events=run_operations(ops_suite,ops_policy,tracer=tracer)
        spans=sanitized_spans(exporter)
    if len(spans) != len(events)+1:
        raise ValueError('OpenTelemetry spans must cover run plus every event')
    benchmark=run_local_benchmark(ops_policy.benchmark_iterations)
    thread_benchmark=run_local_thread_load(ops_policy.benchmark_iterations,workers=4)
    development_gate='PASS' if comparison['status']=='PASS' and ops_report['status']=='PASS' else 'BLOCK'
    incident_count=len(ops_report['incidents'])
    summary={
        'schema_version':'3.0', 'candidate_variant':variant,
        'evaluation_status':'OFFLINE_SYNTHETIC_DEVELOPMENT_ONLY_NO_RELEASE_APPROVAL',
        'overall_development_gate':development_gate,
        'security_evaluation':{'status':comparison['status'],'comparison':comparison,
                               'per_case_evidence':candidate['cases'],
                               'fixture_case_count':len(suite.cases),
                               'reference_expected_to_match':True},
        'operational_fault_injection':ops_report,
        'real_local_cpu_benchmark':benchmark,
        'real_local_thread_load':thread_benchmark,
        'observability':{'structured_event_count':len(events),
                         'dashboard_row_count':len(suite.cases)+len(ops_report['cases']),
                         'otel_span_count':len(spans),'otel_exporter':'SDK_IN_MEMORY_ONLY',
                         'telemetry_kind':'SDK_IN_MEMORY_OPENTELEMETRY_SPANS_AND_OFFLINE_JSONL_EVENTS',
                         'incident_count':incident_count},
        'provenance':{'cp1_report_sha256':hashlib.sha256(cp1_baseline.read_bytes()).hexdigest(),
                      'cp2_report_sha256':hashlib.sha256(cp2_baseline.read_bytes()).hexdigest(),
                      'cp3_fixture_sha256':suite_sha,'cp3_gate_policy_sha256':policy_sha,
                      'cp3_ops_fixture_sha256':ops_sha,'cp3_ops_policy_sha256':ops_policy_sha,
                      'cp2_governance_sha256':cp2_replay['governance_sha256']},
        'security_boundary':{'external_model_calls':0,'external_business_writes':0,
                             'fault_injection_local_only':True,
                             'simulated_results_are_not_production_reliability':True},
        'limitations':['CP3 suite is newly authored and locked locally, but is NOT a blind independent externally curated holdout',
                       'Local reference service ignores injected text by design; passing does not prove real LLM prompt-injection resistance',
                       'Synthetic modeled fault latencies are not actual wall-clock or network latencies',
                       'Thread load is bounded local in-process execution, not HTTP/production throughput',
                       'Small fixed samples cannot estimate production risk, fairness, availability or statistically reliable error rates',
                       'Real OpenTelemetry SDK local spans, but no hosted collector, production service, model provider, or cloud deployment',
                       'Manifest hashes are unsigned and cannot prevent replacement by an actor with full write access'],
    }
    output_dir.mkdir(parents=True,exist_ok=True)
    _write(output_dir/'cp3_report.json',_json(summary))
    _write(output_dir/'cp3_events.jsonl',''.join(json.dumps(event,sort_keys=True,ensure_ascii=True)+'\n' for event in events))
    _write(output_dir/'cp3_spans.jsonl',''.join(json.dumps(span,sort_keys=True,ensure_ascii=True)+'\n' for span in spans))
    rows=[]
    for c in candidate['cases']:
        rows.append({'test_family':'security','case_id':c['case_id'],'category':c['category'],
                     'risk':c['risk'],'expected':c['expected']['decision'],
                     'observed':c['actual'].get('decision','ERROR'),
                     'matched':str(c['passed']).lower(),'attempts':'1','modeled_latency_ms':'',
                     'external_writes':'0','trace_id':''})
    for c in ops_report['cases']:
        rows.append({'test_family':'operational','case_id':c['case_id'],'category':'fault_injection',
                     'risk':'simulation','expected':c['expected_status'],
                     'observed':c['observed_status'],'matched':str(c['matched']).lower(),
                     'attempts':str(c['attempts']),
                     'modeled_latency_ms':str(c['modeled_latency_ms']),
                     'external_writes':'0','trace_id':c['trace_id']})
    out=io.StringIO(newline='')
    cols=['test_family','case_id','category','risk','expected','observed','matched','attempts','modeled_latency_ms','external_writes','trace_id']
    writer=csv.DictWriter(out,fieldnames=cols,lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    _write(output_dir/'cp3_dashboard.csv',out.getvalue())
    manifest={'schema_version':'1.0','filenames':list(FILES),
              'sha256':{name:hashlib.sha256((output_dir/name).read_bytes()).hexdigest() for name in FILES},
              'security_note':'UNSIGNED_LOCAL_SHA256_CHECK_NOT_SIGNATURE'}
    _write(output_dir/'cp3_manifest.json',_json(manifest))
    check=verify_artifacts(output_dir)
    if not check['verified']:
        raise ValueError('Failed to verify generated report artifacts')
    return summary
