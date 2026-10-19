"""Tamper-evident, offline CP1 reference evaluation runner."""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any
from .adapters import LocalReferenceAdapter, LocalResponse
from .cp1_contract import ScenarioSuite

class FixtureIntegrityError(ValueError):
    pass

def load_suite(path: Path) -> tuple[ScenarioSuite, str]:
    payload=path.read_bytes()
    digest=hashlib.sha256(payload).hexdigest()
    sha_path=path.with_suffix('.sha256')
    expected=sha_path.read_text(encoding='utf-8').strip()
    if not (len(expected)==64 and all(x in '0123456789abcdef' for x in expected)):
        raise FixtureIntegrityError("Fixture checksum file has invalid SHA-256 format")
    if digest != expected:
        raise FixtureIntegrityError("Fixture integrity mismatch: expected SHA-256 differs")
    return ScenarioSuite.model_validate_json(payload), digest

def evaluate(suite: ScenarioSuite, fixture_sha256: str, adapter: LocalReferenceAdapter | None = None) -> dict[str, Any]:
    target=adapter if adapter is not None else LocalReferenceAdapter()
    if target.target_id != suite.target_id:
        raise ValueError("Target adapter does not match fixture target_id")
    outcomes=[]
    for case in suite.cases:
        expected=case.expected.model_dump(mode='json')
        try:
            actual=LocalResponse.model_validate(target.invoke(case.payload.model_dump(mode='json'))).model_dump(mode='json')
            passed=actual == expected
            findings=[] if passed else [key for key in expected if actual.get(key)!=expected[key]]
        except Exception as exc:
            actual={"error_type": type(exc).__name__}
            passed=False
            findings=["TARGET_EXECUTION_ERROR"]
        outcomes.append({
            "case_id":case.case_id,
            "category":case.category,
            "risk":case.risk,
            "passed":passed,
            "expected":expected,
            "actual":actual,
            "mismatched_fields":findings,
        })
    by_category={}
    for category in sorted({item['category'] for item in outcomes}):
        group=[item for item in outcomes if item['category']==category]
        by_category[category]={"total":len(group),"passed":sum(item['passed'] for item in group),"failed":sum(not item['passed'] for item in group)}
    count=Counter(item['expected']['decision'] for item in outcomes)
    return {
        "report_schema_version":"1.0", "suite_id":suite.suite_id,
        "target_id":suite.target_id, "fixture_sha256":fixture_sha256,
        "evaluation_type":"offline_deterministic_synthetic_reference",
        "evaluation_status":"DEVELOPMENT_ONLY_NOT_RELEASE_APPROVAL",
        "case_count":len(outcomes),
        "passed_count":sum(item['passed'] for item in outcomes),
        "failed_count":sum(not item['passed'] for item in outcomes),
        "expected_decision_counts":dict(sorted(count.items())),
        "by_category":by_category,
        "cases":outcomes,
        "external_calls":0,
        "consequential_writes":0,
    }

def run_fixture(path: Path, output: Path | None = None) -> dict[str, Any]:
    suite,digest=load_suite(path)
    report=evaluate(suite,digest)
    if output is not None:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    return report
