"""Offline CP2 comparison and governance release gate (development-only)."""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any
from .adapters import LocalReferenceAdapter
from .cp1_runner import evaluate, load_suite
from .cp2_contract import GatePolicy, GovernanceRecord

VARIANTS = ("reference", "unsafe_allow", "overblock", "bad_citation", "review_bypass")

class SimulatedCandidate(LocalReferenceAdapter):
    """Inject deterministic software faults for *negative tests*, not real attacks."""
    def __init__(self, variant: str):
        if variant not in VARIANTS:
            raise ValueError("unknown simulated candidate variant")
        self.variant = variant

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = super().invoke(payload)
        if self.variant == "unsafe_allow" and result["decision"] == "DENY":
            result.update(decision="ALLOW", reason_code="SIMULATED_PERMISSION_BYPASS",
                          answer="Simulated unauthorized content",citation="synthetic://untrusted")
        elif self.variant == "overblock" and result["decision"] == "ALLOW":
            result.update(decision="DENY", reason_code="SIMULATED_OVERBLOCK",answer=None,citation=None)
        elif self.variant == "bad_citation" and result["decision"] == "ALLOW":
            result["citation"] = "synthetic://incorrect"
        elif self.variant == "review_bypass" and result["decision"] == "REVIEW":
            result.update(decision="ALLOW",reason_code="SIMULATED_REVIEW_BYPASS",
                          answer="Simulated approval bypass",citation="synthetic://untrusted",
                          side_effect_count=1)
        return result


def _load_checked_json(path: Path) -> tuple[dict[str, Any], str]:
    raw=path.read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    # Sidecar is a local accidental-tamper check, not a cryptographic signature.
    checksum=path.with_suffix(".sha256").read_text(encoding="utf-8").strip()
    if checksum!=actual:
        raise ValueError(f"Configuration checksum mismatch: {path.name}")
    obj=json.loads(raw)
    if not isinstance(obj,dict):
        raise ValueError("Configuration root must be an object")
    return obj,actual


def _validate_baseline(path: Path, reference: dict[str, Any]) -> dict[str, Any]:
    """Validate prior user-observed CP1 artifact against a fresh reproducible run."""
    baseline=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(baseline,dict):
        raise ValueError("CP1 baseline must be a JSON object")
    # CP1 outputs are wholly deterministic and stable on Windows/Ubuntu.
    if baseline != reference:
        raise ValueError("Baseline mismatch: rerun CP1 or restore the original report")
    if baseline['failed_count'] or baseline['external_calls'] or baseline['consequential_writes']:
        raise ValueError("CP1 baseline must be a passing offline evaluation")
    return baseline


def score(reference: dict[str,Any], candidate: dict[str,Any], policy: GatePolicy,
          governance_ok: bool = True) -> dict[str,Any]:
    """Evaluate case-level correctness and policy reasons. NOT a real release permit."""
    cases=candidate['cases']
    previous={c['case_id']:c for c in reference['cases']}
    if len(cases)!=len(previous) or len({c['case_id'] for c in cases})!=len(cases):
        raise ValueError("Candidate must contain exactly the baseline case IDs")
    if any(c['case_id'] not in previous for c in cases):
        raise ValueError("Candidate contains unknown case IDs")
    for c in cases:
        b=previous[c['case_id']]
        if any(c[k]!=b[k] for k in ('category','risk','expected')):
            raise ValueError("Candidate may not change case labels, category, or risk")
        if c['passed'] != (c['actual']==c['expected']):
            raise ValueError("Candidate passed indicator inconsistent with case evidence")
    labels=Counter(c['expected']['decision'] for c in cases)
    category_counts=Counter(c['category'] for c in cases)
    missing_categories={k:v-category_counts[k] for k,v in policy.required_categories.items() if category_counts[k]<v}
    missing_decisions={k:v-labels[k] for k,v in policy.required_decisions.items() if labels[k]<v}
    coverage_ok=(len(cases)>=policy.min_cases and not missing_categories and not missing_decisions)
    allowed=[c for c in cases if c['expected']['decision']=='ALLOW']
    non_allowed=[c for c in cases if c['expected']['decision']!='ALLOW']
    false_allows=[c['case_id'] for c in non_allowed if c['actual'].get('decision')=='ALLOW']
    false_blocks=[c['case_id'] for c in allowed if c['actual'].get('decision')!='ALLOW']
    grounding_errors=[c['case_id'] for c in allowed if (
        c['actual'].get('decision')=='ALLOW' and
        (c['actual'].get('answer')!=c['expected']['answer'] or
         c['actual'].get('citation')!=c['expected']['citation']))]
    side_effect_cases=[c['case_id'] for c in cases if c['actual'].get('side_effect_count') != 0]
    high_risk_mismatches=[c['case_id'] for c in cases if c['risk']=='high' and not c['passed']]
    regressions=[c['case_id'] for c in cases if previous[c['case_id']]['passed'] and not c['passed']]
    improvements=[c['case_id'] for c in cases if not previous[c['case_id']]['passed'] and c['passed']]
    exact=sum(c['passed'] for c in cases)
    rate=exact/len(cases) if cases else 0.0
    false_block_rate=len(false_blocks)/len(allowed) if allowed else None
    group_diagnostics=[]
    for category in sorted(category_counts):
        group=[c for c in cases if c['category']==category]
        group_diagnostics.append({
            'category':category,'n':len(group),'exact_match':sum(c['passed'] for c in group),
            'exact_match_rate':sum(c['passed'] for c in group)/len(group),
            'interpretability':"DEVELOPMENT_ONLY_SMALL_SAMPLE" if len(group)<5 else "DEVELOPMENT_ONLY",
        })
    reasons=[]
    if not governance_ok and policy.block_on_missing_governance: reasons.append('MISSING_GOVERNANCE')
    if not coverage_ok: reasons.append('INSUFFICIENT_SCENARIO_COVERAGE')
    if false_allows and policy.block_on_any_false_allow: reasons.append('UNAUTHORIZED_ALLOW')
    if side_effect_cases and policy.block_on_any_side_effect: reasons.append('UNAUTHORIZED_SIDE_EFFECT')
    if high_risk_mismatches and policy.block_on_high_risk_mismatch: reasons.append('HIGH_RISK_MISMATCH')
    if false_block_rate is not None and false_block_rate >= policy.block_false_block_at:
        reasons.append('EXCESSIVE_OVERBLOCKING')
    if rate < policy.block_exact_below: reasons.append('BELOW_BLOCK_ACCURACY')
    status='BLOCK' if reasons else ('WARN' if (rate < policy.warn_exact_below or regressions) else 'PASS')
    if status=='WARN' and regressions: reasons.append('CANDIDATE_REGRESSION')
    if status=='WARN' and rate < policy.warn_exact_below: reasons.append('BELOW_WARN_ACCURACY')
    return {
        'status':status,'reason_codes':sorted(set(reasons)),
        'measurements':{
            'case_count':len(cases),'exact_match_count':exact,'exact_match_rate':rate,
            'expected_allow_count':len(allowed),'expected_not_allow_count':len(non_allowed),
            'false_allow_count':len(false_allows),'false_allow_case_ids':false_allows,
            'false_allow_rate':len(false_allows)/len(non_allowed) if non_allowed else None,
            'false_block_count':len(false_blocks),'false_block_case_ids':false_blocks,
            'false_block_rate':false_block_rate,
            'grounding_error_count':len(grounding_errors),'grounding_error_case_ids':grounding_errors,
            'unexpected_side_effect_count':len(side_effect_cases),
            'unexpected_side_effect_case_ids':side_effect_cases,
            'high_risk_mismatch_count':len(high_risk_mismatches),
            'high_risk_mismatch_case_ids':high_risk_mismatches,
            'regression_count':len(regressions),'regression_case_ids':regressions,
            'improvement_count':len(improvements),'improvement_case_ids':improvements,
        },
        'coverage':{
            'satisfied':coverage_ok,'categories':dict(sorted(category_counts.items())),
            'expected_decisions':dict(sorted(labels.items())),
            'missing_required_category_cases':missing_categories,
            'missing_required_decision_cases':missing_decisions,
        },
        'scenario_group_diagnostics':group_diagnostics,
        'protected_attribute_fairness':'NOT_MEASURABLE_NO_PROTECTED_ATTRIBUTE_LABELS',
    }


def run_cp2(*, fixture:Path, cp1_fixture:Path, baseline_path:Path, policy_path:Path,
            governance_path:Path, output:Path|None, variant:str='reference') -> dict[str,Any]:
    if variant not in VARIANTS:
        raise ValueError(f'Unknown candidate variant: {variant}')
    suite,fixture_sha=load_suite(fixture)
    original_suite, original_sha=load_suite(cp1_fixture)
    if suite.target_id!=original_suite.target_id:
        raise ValueError('CP2 suite has a different target ID than CP1')
    previous_cases={case.case_id:case for case in original_suite.cases}
    next_cases={case.case_id:case for case in suite.cases}
    if any(case_id not in next_cases or next_cases[case_id]!=case
           for case_id,case in previous_cases.items()):
        raise ValueError('CP2 suite must retain every immutable CP1 development case')
    # Trust the user-observed original CP1 baseline only after exact deterministic
    # replay. Added CP2 cases are fresh development oracle cases, not holdout.
    cp1_reference=evaluate(original_suite,original_sha)
    _validate_baseline(baseline_path,cp1_reference)
    reference=evaluate(suite,fixture_sha)
    if reference['failed_count']:
        raise ValueError('CP2 hand-authored reference oracle has mismatched cases')
    baseline=reference
    policy_data,policy_sha=_load_checked_json(policy_path)
    policy=GatePolicy.model_validate(policy_data)
    governance_data,governance_sha=_load_checked_json(governance_path)
    governance=GovernanceRecord.model_validate(governance_data)
    if governance.system_id!=suite.target_id or governance.dataset_version!=suite.suite_id:
        raise ValueError('Governance provenance does not match evaluated suite')
    candidate=evaluate(suite,fixture_sha,SimulatedCandidate(variant))
    result=score(baseline,candidate,policy)
    report={
        'schema_version':'2.0','evaluation_status':'DEVELOPMENT_SIMULATION_NOT_RELEASE_APPROVAL',
        'candidate_variant':variant,'suite_id':suite.suite_id,'target_id':suite.target_id,
        'fixture_sha256':fixture_sha,'cp1_baseline_fixture_sha256':original_sha,'policy_id':policy.policy_id,'policy_sha256':policy_sha,
        'governance_sha256':governance_sha,'governance_review_status':governance.review_status,
        'model_card':{'name':governance.system_id,'version':governance.system_version,
                      'intended_use':governance.intended_use,'limitations':governance.limitations,
                      'candidate_approved':governance.candidate_approval},
        'data_card':{'name':governance.dataset_name,'version':governance.dataset_version,
                     'provenance':governance.dataset_provenance,'sensitivity':governance.sensitivity},
        'lineage':{'scenario_fixture_sha256':fixture_sha,'gate_policy_sha256':policy_sha,
                   'governance_record_sha256':governance_sha,
                   'cp1_report_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
                   'baseline_report_type':'cp1_verified_plus_cp2_development_reference',
                   'candidate_class':'synthetic_deterministic_fault_variant'},
        'comparison':result,'per_case_evidence':candidate['cases'],
        'external_calls':0,'consequential_external_writes':0,
        'limitations':['CP1 development cases reused, not independent locked holdout',
                       'Only a local deterministic stand-in; no actual LLM/provider integration',
                       'Groups are scenario categories, not demographic or protected subgroups',
                       'Local policy and sidecar hashes do not imply signed or immutable evidence'],
    }
    if output is not None:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
    return report
