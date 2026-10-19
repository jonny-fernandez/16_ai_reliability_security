"""Project 16 offline evaluation CLI (no provider key or network required)."""
from __future__ import annotations
import argparse
from pathlib import Path
from .cp1_runner import run_fixture
from .cp2_runner import run_cp2, VARIANTS
from .cp3_runner import run_cp3, verify_artifacts

def main() -> int:
    parser=argparse.ArgumentParser(description='Project 16 offline reliability evaluations')
    parser.add_argument('checkpoint',choices=['cp1','cp2','cp3','cp3-verify'])
    parser.add_argument('--fixture',type=Path,default=Path('data/fixtures/cp1_scenarios.json'))
    parser.add_argument('--output',type=Path,default=None)
    parser.add_argument('--cp1-fixture',type=Path,default=Path('data/fixtures/cp1_scenarios.json'))
    parser.add_argument('--baseline',type=Path,default=Path('outputs/cp1_baseline_report.json'))
    parser.add_argument('--policy',type=Path,default=Path('configs/cp2_gate_policy.json'))
    parser.add_argument('--governance',type=Path,default=Path('configs/cp2_governance.json'))
    parser.add_argument('--variant',choices=VARIANTS,default='reference',
                        help='CP2 synthetic candidate, reference is the normal validation')
    parser.add_argument('--output-dir',type=Path,default=Path('outputs/cp3_reference'))
    parser.add_argument('--cp2-baseline',type=Path,default=Path('outputs/cp2_development_gate_report.json'))
    args=parser.parse_args()
    if args.checkpoint == 'cp3-verify':
        try:
            verified=verify_artifacts(args.output_dir)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            print(f'CP3 INTEGRITY ERROR: {type(exc).__name__}: {exc}')
            return 2
        print(f"CP3 integrity verified: files={verified['artifact_count']} events={verified['event_count']} dashboard_rows={verified['dashboard_rows']} status={verified['status']}")
        print('Unsigned SHA-256 file integrity only; not a signature or production release.')
        return 0
    if args.checkpoint=='cp3':
        try:
            report=run_cp3(cp1_fixture=args.cp1_fixture,
                           cp2_fixture=Path('data/fixtures/cp2_scenarios.json'),
                           cp3_fixture=Path('data/fixtures/cp3_security_scenarios.json'),
                           cp1_baseline=args.baseline,cp2_baseline=args.cp2_baseline,
                           cp2_policy=args.policy,cp2_governance=args.governance,
                           cp3_policy=Path('configs/cp3_gate_policy.json'),
                           operational_fixture=Path('data/fixtures/cp3_operations.json'),
                           operational_policy=Path('configs/cp3_ops_policy.json'),
                           output_dir=args.output_dir,variant=args.variant)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            print(f'CP3 ERROR: {type(exc).__name__}: {exc}')
            return 2
        security=report['security_evaluation']['comparison']['measurements']
        ops=report['operational_fault_injection']
        benchmark=report['real_local_cpu_benchmark']
        print(f"CP3 variant={args.variant}: gate={report['overall_development_gate']} security={security['exact_match_count']}/{security['case_count']} operational={ops['expected_behavior_matched']}/{ops['case_count']}")
        print(f"CP3 attempts={ops['attempt_count']} retries={ops['retry_count']} recovered={ops['recovered_requests']} replayed={ops['duplicate_replays']} external_calls=0 writes=0")
        print(f"Local measured benchmark: {benchmark['iterations']} sequential calls, p95={benchmark['p95_ms']:.4f} ms (NOT hosted/network load)")
        print(f'Artifacts: {args.output_dir}')
        print('LOCAL OFFLINE DEVELOPMENT evaluation; NOT approval for production deployment.')
        return 0 if report['overall_development_gate']=='PASS' else 1
    if args.checkpoint=='cp1':
        dest=args.output or Path('outputs/cp1_baseline_report.json')
        try:
            report=run_fixture(args.fixture,dest)
        except (OSError,ValueError) as exc:
            print(f'CP1 ERROR: {type(exc).__name__}: {exc}')
            return 2
        print(f"CP1 synthetic reference: {report['passed_count']}/{report['case_count']} cases passed, "
              f"{report['failed_count']} failed; external_calls={report['external_calls']}; "
              f"writes={report['consequential_writes']}")
        print(f"Fixture SHA-256: {report['fixture_sha256']}")
        print(f'Report: {dest}')
        print('CP1 validation PASSED (development fixture, not a release decision)' if not report['failed_count']
              else 'CP1 validation FAILED (not a release decision)')
        return 0 if not report['failed_count'] else 1
    dest=args.output or Path('outputs/cp2_development_gate_report.json')
    fixture=args.fixture if args.fixture != Path('data/fixtures/cp1_scenarios.json') else Path('data/fixtures/cp2_scenarios.json')
    try:
        report=run_cp2(fixture=fixture,cp1_fixture=args.cp1_fixture,baseline_path=args.baseline,policy_path=args.policy,
                       governance_path=args.governance,output=dest,variant=args.variant)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'CP2 ERROR: {type(exc).__name__}: {exc}')
        return 2
    gate=report['comparison']
    metrics=gate['measurements']
    print(f"CP2 candidate={args.variant}: development gate={gate['status']} "
          f"exact={metrics['exact_match_count']}/{metrics['case_count']} "
          f"false_allow={metrics['false_allow_count']} false_block={metrics['false_block_count']} "
          f"regressions={metrics['regression_count']}")
    print(f"Reasons: {', '.join(gate['reason_codes']) or '(none)'}")
    print(f'Report: {dest}')
    print('CP2 is a LOCAL DEVELOPMENT simulation, not authorization for production release.')
    return 0 if gate['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
