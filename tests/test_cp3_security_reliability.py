"""CP3 actual offline security, SLI and evidence test gates (no external services)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
from collections import Counter
import pytest
from pydantic import ValidationError

from ai_reliability.cp1_runner import load_suite
from ai_reliability.cp2_runner import run_cp2
from ai_reliability.cp3_contract import OperationalSuite, OperationalPolicy
from ai_reliability.cp3_operations import run_operations, run_local_benchmark, run_local_thread_load, percentile
from ai_reliability.cp3_runner import run_cp3, verify_artifacts

ROOT=Path(__file__).resolve().parents[1]


def args(tmp_path:Path,variant='reference') -> dict:
    baseline=tmp_path/'cp1_baseline_report.json'
    cp2_base=tmp_path/'cp2_development_gate_report.json'
    # Reproduce earlier passing local baselines. This is not a production approval.
    from ai_reliability.cp1_runner import run_fixture
    run_fixture(ROOT/'data/fixtures/cp1_scenarios.json',baseline)
    run_cp2(fixture=ROOT/'data/fixtures/cp2_scenarios.json',
            cp1_fixture=ROOT/'data/fixtures/cp1_scenarios.json',baseline_path=baseline,
            policy_path=ROOT/'configs/cp2_gate_policy.json',
            governance_path=ROOT/'configs/cp2_governance.json',output=cp2_base)
    return dict(cp1_fixture=ROOT/'data/fixtures/cp1_scenarios.json',
                cp2_fixture=ROOT/'data/fixtures/cp2_scenarios.json',
                cp3_fixture=ROOT/'data/fixtures/cp3_security_scenarios.json',
                cp1_baseline=baseline,cp2_baseline=cp2_base,
                cp2_policy=ROOT/'configs/cp2_gate_policy.json',
                cp2_governance=ROOT/'configs/cp2_governance.json',
                cp3_policy=ROOT/'configs/cp3_gate_policy.json',
                operational_fixture=ROOT/'data/fixtures/cp3_operations.json',
                operational_policy=ROOT/'configs/cp3_ops_policy.json',
                output_dir=tmp_path/('cp3_'+variant),variant=variant)


def test_separate_locked_suite_and_oracle_coverage():
    suite,_=load_suite(ROOT/'data/fixtures/cp3_security_scenarios.json')
    cp2,_=load_suite(ROOT/'data/fixtures/cp2_scenarios.json')
    assert len(suite.cases)==20
    assert not {c.case_id for c in suite.cases}&{c.case_id for c in cp2.cases}
    assert Counter(c.category for c in suite.cases)=={
        'legitimate':2,'authorization':8,'injection':6,'approval':2,'unknown_resource':2}
    assert Counter(c.expected.decision for c in suite.cases)=={'ALLOW':5,'DENY':11,'REVIEW':2,'ABSTAIN':2}


def test_original_baseline_preserved(tmp_path):
    kw=args(tmp_path)
    report=run_cp3(**kw)
    assert report['provenance']['cp1_report_sha256']==hashlib.sha256(kw['cp1_baseline'].read_bytes()).hexdigest()
    assert report['provenance']['cp2_report_sha256']==hashlib.sha256(kw['cp2_baseline'].read_bytes()).hexdigest()


def test_cp3_reference_passes_measured_categories(tmp_path):
    report=run_cp3(**args(tmp_path))
    comparison=report['security_evaluation']['comparison']
    metrics=comparison['measurements']
    assert report['overall_development_gate']=='PASS'
    assert metrics['case_count']==20 and metrics['exact_match_count']==20
    for field in ('false_allow_count','false_block_count','grounding_error_count',
                  'unexpected_side_effect_count','high_risk_mismatch_count'):
        assert metrics[field]==0
    assert report['security_boundary']['external_model_calls']==0
    assert report['security_boundary']['external_business_writes']==0


@pytest.mark.parametrize('variant,metric,expected',[
    ('unsafe_allow','false_allow_count',11),
    ('overblock','false_block_count',5),
    ('bad_citation','grounding_error_count',5),
    ('review_bypass','unexpected_side_effect_count',2),
])
def test_negative_security_candidates_block(tmp_path,variant,metric,expected):
    report=run_cp3(**args(tmp_path,variant))
    assert report['overall_development_gate']=='BLOCK'
    values=report['security_evaluation']['comparison']['measurements']
    assert values[metric]==expected
    assert report['security_boundary']['external_business_writes']==0


def test_operations_retries_fallback_replay_and_breaker():
    from ai_reliability.cp2_runner import _load_checked_json
    specs,_=_load_checked_json(ROOT/'data/fixtures/cp3_operations.json')
    cfg,_=_load_checked_json(ROOT/'configs/cp3_ops_policy.json')
    report,events=run_operations(OperationalSuite.model_validate(specs),OperationalPolicy.model_validate(cfg))
    assert report['status']=='PASS'
    assert report['expected_behavior_matched']==report['case_count']==12
    assert report['attempt_count']==20 and report['retry_count']==10
    assert report['recovered_requests']==2 and report['duplicate_replays']==1
    assert report['side_effect_count']==0 and report['external_calls']==0
    assert len(events)==32
    by_id={c['case_id']:c for c in report['cases']}
    assert by_id['op_09_idempotent_replay']['attempts']==0
    assert by_id['op_12_open_circuit']['attempts']==0
    assert by_id['op_07_safe_fallback']['observed_status']=='DEGRADED_ABSTAIN'
    assert by_id['op_05_auth_fail_closed']['attempts']==1
    assert by_id['op_04_malformed_fail_closed']['attempts']==1


def test_simulated_slo_not_conflated_with_benchmark():
    from ai_reliability.cp2_runner import _load_checked_json
    specs,_=_load_checked_json(ROOT/'data/fixtures/cp3_operations.json')
    cfg,_=_load_checked_json(ROOT/'configs/cp3_ops_policy.json')
    summary,_=run_operations(OperationalSuite.model_validate(specs),OperationalPolicy.model_validate(cfg))
    window=summary['simulated_window_sli']
    assert window['measurement_type']=='SYNTHETIC_INJECTED_FAULT_WINDOW_NOT_REAL_AVAILABILITY'
    assert window['observations']==12
    assert window['would_breach_simulated_targets']
    assert window['actual_rollback_triggered'] is False
    assert summary['status']=='PASS'  # correct handling != satisfactory simulated availability
    assert all(i['real_incident'] is False for i in summary['incidents'])


def test_hardware_benchmark_is_measured_sequential_not_fabricated():
    result=run_local_benchmark(101)
    assert result['iterations']==101 and result['parallelism']==1
    assert result['measurement_type']=='REAL_LOCAL_CPU_INVOCATION_TIMING_NOT_NETWORK_LOAD'
    assert result['p95_ms'] >= 0 and result['max_ms'] >= result['p95_ms']
    assert result['wall_clock_elapsed_ms']>0 and result['external_requests']==0


@pytest.mark.parametrize('n',[0,3,99,2001])
def test_benchmark_workload_bounded(n):
    with pytest.raises(ValueError):
        run_local_benchmark(n)


def test_real_bounded_concurrent_local_load():
    data=run_local_thread_load(105,workers=4)
    assert data["observed_success_count"]==data["iterations"]==105
    assert data["threads"]==4 and data["external_requests"]==0
    assert data["measurement_type"]=="REAL_LOCAL_THREADED_CPU_LOAD_NOT_HOSTED_API_OR_HTTP"
    assert data["p95_call_ms"]>=0 and data["wall_clock_elapsed_ms"]>0


@pytest.mark.parametrize("workers,iterations",[(0,100),(9,100),(4,99),(4,2001)])
def test_local_thread_load_limits(workers,iterations):
    with pytest.raises(ValueError):
        run_local_thread_load(iterations,workers)


def test_percentile_semantics():
    assert percentile([],0.95) is None
    assert percentile([1,2,3,4,5],.95)==5
    assert percentile([1,2,3,4,5],.5)==3
    with pytest.raises(ValueError):
        percentile([1],2)


def test_real_otel_spans_are_exported_only_in_memory(tmp_path):
    report=run_cp3(**args(tmp_path))
    d=tmp_path/'cp3_reference'
    spans=[json.loads(line) for line in (d/'cp3_spans.jsonl').read_text().splitlines()]
    assert report['observability']['otel_exporter']=='SDK_IN_MEMORY_ONLY'
    assert len(spans)==33
    assert any(s['name']=='cp3.offline_fault_injection' and s['parent_span_id'] is None for s in spans)
    assert sum(s['parent_span_id'] is not None for s in spans)==32
    assert all(s['network_exported'] is False for s in spans)
    assert all('prompt' not in json.dumps(s).lower() for s in spans)


def test_artifact_integrity_passes(tmp_path):
    run_cp3(**args(tmp_path))
    check=verify_artifacts(tmp_path/'cp3_reference')
    assert check['verified'] and check['artifact_count']==4
    assert check['event_count']==32 and check['dashboard_rows']==32


@pytest.mark.parametrize('file', ['cp3_report.json','cp3_events.jsonl','cp3_spans.jsonl','cp3_dashboard.csv'])
def test_changed_evidence_fails_integrity(tmp_path,file):
    run_cp3(**args(tmp_path))
    directory=tmp_path/'cp3_reference'
    with (directory/file).open('a',encoding='utf-8') as f:
        f.write('tampered\n')
    with pytest.raises(ValueError,match='integrity mismatch'):
        verify_artifacts(directory)


def test_renamed_manifest_entry_fails_closed(tmp_path):
    run_cp3(**args(tmp_path))
    directory=tmp_path/'cp3_reference'
    manifest=directory/'cp3_manifest.json'
    j=json.loads(manifest.read_text())
    j['filenames'][0]='../secrets.txt'
    manifest.write_text(json.dumps(j))
    with pytest.raises(ValueError,match='filenames mismatch'):
        verify_artifacts(directory)


def test_cp2_baseline_tamper_is_detected(tmp_path):
    kw=args(tmp_path)
    base=json.loads(kw['cp2_baseline'].read_text())
    base['comparison']['status']='BLOCK'
    kw['cp2_baseline'].write_text(json.dumps(base))
    with pytest.raises(ValueError,match='CP2 baseline mismatch'):
        run_cp3(**kw)


def test_cp3_fixture_tamper_is_detected(tmp_path):
    kw=args(tmp_path)
    path=tmp_path/'cp3_security_scenarios.json'
    shutil.copyfile(kw['cp3_fixture'],path)
    shutil.copyfile(kw['cp3_fixture'].with_suffix('.sha256'),path.with_suffix('.sha256'))
    path.write_text(path.read_text().replace('holdout_public_lookup','holdout_corrupted_lookup'))
    kw['cp3_fixture']=path
    with pytest.raises(ValueError,match='integrity mismatch'):
        run_cp3(**kw)


def test_cp3_policy_tamper_is_detected(tmp_path):
    kw=args(tmp_path)
    path=tmp_path/'cp3_gate_policy.json'
    shutil.copyfile(kw['cp3_policy'],path)
    shutil.copyfile(kw['cp3_policy'].with_suffix('.sha256'),path.with_suffix('.sha256'))
    path.write_text(path.read_text().replace('0.85','0.80'))
    kw['cp3_policy']=path
    with pytest.raises(ValueError,match='checksum mismatch'):
        run_cp3(**kw)


def test_operations_suite_rejects_duplicate_case_ids():
    from ai_reliability.cp2_runner import _load_checked_json
    specs,_=_load_checked_json(ROOT/'data/fixtures/cp3_operations.json')
    specs['cases'][1]['case_id']=specs['cases'][0]['case_id']
    with pytest.raises(ValidationError,match='Duplicate operational case IDs'):
        OperationalSuite.model_validate(specs)


def test_operations_policy_rejects_unbounded_retries():
    from ai_reliability.cp2_runner import _load_checked_json
    policy,_=_load_checked_json(ROOT/'configs/cp3_ops_policy.json')
    policy['max_attempts']=999
    with pytest.raises(ValidationError):
        OperationalPolicy.model_validate(policy)
