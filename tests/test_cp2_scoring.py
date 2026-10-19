"""CP2 positive/negative, provenance, governance and release-gate tests."""
import hashlib
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from ai_reliability.cp1_runner import load_suite, evaluate
from ai_reliability.cp2_contract import GatePolicy, GovernanceRecord
from ai_reliability.cp2_runner import run_cp2,score,SimulatedCandidate,_load_checked_json,VARIANTS

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'data/fixtures/cp1_scenarios.json'
CP2_FIXTURE=ROOT/'data/fixtures/cp2_scenarios.json'
POLICY=ROOT/'configs/cp2_gate_policy.json'
GOVERNANCE=ROOT/'configs/cp2_governance.json'

@pytest.fixture
def inputs(tmp_path):
    suite,sha=load_suite(FIXTURE)
    baseline=evaluate(suite,sha)
    p=tmp_path/'cp1_baseline_report.json'
    p.write_text(json.dumps(baseline),encoding='utf-8')
    return {'fixture':CP2_FIXTURE,'cp1_fixture':FIXTURE,'baseline_path':p,'policy_path':POLICY,'governance_path':GOVERNANCE,'output':None}

def _run(inputs,variant='reference'):
    return run_cp2(**inputs,variant=variant)

def test_reference_passes_with_checksum_provenance_fields(inputs):
    report=_run(inputs)
    assert report['comparison']['status']=='PASS'
    assert report['comparison']['measurements']['exact_match_count']==20
    assert report['comparison']['measurements']['false_allow_count']==0
    assert report['comparison']['measurements']['false_block_count']==0
    assert report['comparison']['measurements']['regression_count']==0
    assert report['governance_review_status']=='DEVELOPMENT_UNAPPROVED'
    assert not report['model_card']['candidate_approved']
    assert report['external_calls']==report['consequential_external_writes']==0
    assert report['comparison']['coverage']['satisfied']
    assert report['evaluation_status']!='RELEASE_APPROVED'
    assert len(report['per_case_evidence'])==20

@pytest.mark.parametrize('variant,reasons',[
    ('unsafe_allow',{'UNAUTHORIZED_ALLOW','HIGH_RISK_MISMATCH'}),
    ('overblock',{'EXCESSIVE_OVERBLOCKING','HIGH_RISK_MISMATCH'}),
    ('bad_citation',{'HIGH_RISK_MISMATCH'}),
    ('review_bypass',{'UNAUTHORIZED_ALLOW','UNAUTHORIZED_SIDE_EFFECT','HIGH_RISK_MISMATCH'}),
])
def test_faulty_candidates_are_blocked(inputs,variant,reasons):
    result=_run(inputs,variant)['comparison']
    assert result['status']=='BLOCK'
    assert reasons.issubset(result['reason_codes'])
    assert result['measurements']['regression_count']>0

@pytest.mark.parametrize('variant',VARIANTS)
def test_repeated_evaluations_are_deterministic(inputs,variant):
    assert _run(inputs,variant)==_run(inputs,variant)

def test_cp1_regression_baseline_rejects_tampered_metrics(inputs):
    path=inputs['baseline_path']
    baseline=json.loads(path.read_text());baseline['passed_count']=42
    path.write_text(json.dumps(baseline))
    with pytest.raises(ValueError,match='Baseline mismatch'):
        _run(inputs)

def test_baseline_rejects_modified_expected_labels(inputs):
    path=inputs['baseline_path']
    baseline=json.loads(path.read_text());baseline['cases'][0]['expected']['decision']='DENY'
    path.write_text(json.dumps(baseline))
    with pytest.raises(ValueError,match='Baseline mismatch'):
        _run(inputs)

def test_gate_policy_sidecar_rejects_tamper(inputs,tmp_path):
    p=tmp_path/'policy.json'; p.write_bytes(POLICY.read_bytes()+b' ')
    p.with_suffix('.sha256').write_bytes(POLICY.with_suffix('.sha256').read_bytes())
    inputs['policy_path']=p
    with pytest.raises(ValueError,match='checksum mismatch'):
        _run(inputs)

def test_governance_sidecar_rejects_tamper(inputs,tmp_path):
    p=tmp_path/'governance.json';p.write_bytes(GOVERNANCE.read_bytes()+b' ')
    p.with_suffix('.sha256').write_bytes(GOVERNANCE.with_suffix('.sha256').read_bytes())
    inputs['governance_path']=p
    with pytest.raises(ValueError,match='checksum mismatch'):
        _run(inputs)

def test_missing_governance_is_fatal(inputs,tmp_path):
    inputs['governance_path']=tmp_path/'missing.json'
    with pytest.raises(FileNotFoundError):_run(inputs)

def test_rejects_insecure_gate_threshold_changes():
    data=json.loads(POLICY.read_text());data['block_on_any_false_allow']=False
    with pytest.raises(ValidationError,match='critical safety checks'):
        GatePolicy.model_validate(data)

def test_rejects_bad_governance_approval_label():
    data=json.loads(GOVERNANCE.read_text());data['review_status']='PRODUCTION_APPROVED'
    with pytest.raises(ValidationError):GovernanceRecord.model_validate(data)

def test_policy_sha_matches_actual_file():
    _,actual=_load_checked_json(POLICY)
    assert hashlib.sha256(POLICY.read_bytes()).hexdigest()==actual

def test_fairness_claim_does_not_exceed_available_data(inputs):
    result=_run(inputs)['comparison']
    assert result['protected_attribute_fairness']=='NOT_MEASURABLE_NO_PROTECTED_ATTRIBUTE_LABELS'
    assert set(x['category'] for x in result['scenario_group_diagnostics']) == {
        'approval','authorization','injection','legitimate','unknown_resource'}

def test_coverage_gate_blocks_missing_critical_category(inputs):
    suite,sha=load_suite(CP2_FIXTURE)
    full=evaluate(suite,sha)
    candidate=evaluate(suite,sha)
    # One category removed, avoiding artificial backfilling of scenario coverage.
    candidate['cases']=[x for x in candidate['cases'] if x['category']!='approval']
    reference={'cases':list(candidate['cases'])}
    policy=GatePolicy.model_validate(json.loads(POLICY.read_text()))
    assessed=score(reference,candidate,policy)
    assert assessed['status']=='BLOCK'
    assert assessed['coverage']['missing_required_category_cases']=={'approval':2}
    assert 'INSUFFICIENT_SCENARIO_COVERAGE' in assessed['reason_codes']

def test_high_risk_mismatch_blocks_even_if_total_accuracy_high(inputs):
    suite,sha=load_suite(CP2_FIXTURE)
    reference=evaluate(suite,sha);candidate=evaluate(suite,sha)
    case=next(c for c in candidate['cases'] if c['risk']=='high')
    case['actual']['reason_code']='WRONG_REASON'
    case['passed']=False
    policy=GatePolicy.model_validate(json.loads(POLICY.read_text()))
    assessed=score(reference,candidate,policy)
    assert assessed['measurements']['exact_match_rate']==0.95
    assert assessed['status']=='BLOCK'
    assert 'HIGH_RISK_MISMATCH' in assessed['reason_codes']

def test_medium_risk_single_mismatch_warns_not_pass(inputs):
    suite,sha=load_suite(CP2_FIXTURE)
    baseline=evaluate(suite,sha)
    candidate=evaluate(suite,sha)
    case=next(c for c in candidate['cases'] if c['risk']=='medium' and c['expected']['decision']=='DENY')
    case['actual']['reason_code']='DIFFERENT_DENIAL_CODE'
    case['passed']=False
    policy=GatePolicy.model_validate(json.loads(POLICY.read_text()))
    assessed=score(baseline,candidate,policy)
    assert assessed['status']=='WARN'
    assert 'CANDIDATE_REGRESSION' in assessed['reason_codes']

def test_reject_changed_candidate_oracle(inputs):
    suite,sha=load_suite(CP2_FIXTURE)
    baseline=evaluate(suite,sha);candidate=evaluate(suite,sha)
    candidate['cases'][0]['expected']['decision']='DENY'
    policy=GatePolicy.model_validate(json.loads(POLICY.read_text()))
    with pytest.raises(ValueError,match='may not change'):
        score(baseline,candidate,policy)

def test_cp2_report_file_is_serializable(inputs,tmp_path):
    output=tmp_path/'report.json'
    inputs['output']=output
    report=_run(inputs)
    assert json.loads(output.read_text(encoding='utf-8'))==report
    assert output.read_bytes().endswith(b'\n')

def test_unknown_variant_fails_fast(inputs):
    with pytest.raises(ValueError,match='Unknown candidate'):
        _run(inputs,'new_variant')

def test_no_secret_file_in_repository_delivery():
    # Normal source layout may have local .env in a developer checkout;
    # this test only verifies the published example is a harmless placeholder.
    assert 'REPLACE_WITH_YOUR_OWN_KEY' in (ROOT/'.env.example').read_text()


def test_cp2_suite_must_retain_unmodified_cp1_cases(inputs,tmp_path):
    suite=json.loads(CP2_FIXTURE.read_text())
    suite['cases'][0]['payload']['scopes']=['bogus:permission']
    fixture=tmp_path/'altered_cp2.json'
    fixture.write_text(json.dumps(suite),encoding='utf-8')
    fixture.with_suffix('.sha256').write_text(hashlib.sha256(fixture.read_bytes()).hexdigest()+'\n')
    inputs['fixture']=fixture
    with pytest.raises(ValueError,match='immutable CP1'):
        _run(inputs)
