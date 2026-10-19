"""Bounded, entirely offline fault injection, trace metadata, and measured local benchmark.

Simulated fault latencies are intentionally NOT hardware/network observations.
No real service requests, persistence side effects, or fault-causing sleeps occur.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import math
import platform
import statistics
import sys
from time import perf_counter_ns
from typing import Any
from .adapters import LocalReferenceAdapter
from .cp3_contract import OperationalPolicy, OperationalSuite
from .ops.incidents import incident_severity

FAULT_MODEL_MS = {'ok':8, 'timeout':1000, 'rate_limit':50, 'malformed_json':10, 'auth_failure':8}
RETRYABLE = {'timeout','rate_limit'}


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if not 0 <= q <= 1:
        raise ValueError('Percentile must lie in [0,1]')
    ordered=sorted(values)
    return ordered[max(0,math.ceil(q*len(ordered))-1)]


def _trace_id(case_id: str) -> str:
    return hashlib.sha256(('cp3-local:'+case_id).encode('utf-8')).hexdigest()[:24]


def run_operations(suite: OperationalSuite, policy: OperationalPolicy, tracer: Any = None) -> tuple[dict[str,Any],list[dict[str,Any]]]:
    if len(suite.cases) < policy.required_operational_cases:
        raise ValueError('Operational case coverage below locked policy')
    replay_cache: set[str] = set()
    breaker_failures: defaultdict[str,int] = defaultdict(int)
    events: list[dict[str,Any]]=[]
    outcomes: list[dict[str,Any]]=[]
    attempts_by_kind: Counter[str] = Counter()
    def emit(event: dict[str,Any]):
        events.append(event)
        if tracer is not None:
            attrs={key:value for key,value in event.items()
                   if key in {'case_id','event_type','fault_kind','attempt','modeled_latency_ms'}}
            with tracer.start_as_current_span('cp3.local.event',attributes=attrs):
                pass
    for case in suite.cases:
        case_id=case.case_id
        trace=_trace_id(case_id)
        attempts=0
        modeled_ms=0
        simulated_result='FAILED_CLOSED'
        if case.idempotency_key and case.idempotency_key in replay_cache:
            simulated_result='REPLAYED'
        elif case.circuit and breaker_failures[case.circuit]>=policy.breaker_after_failed_requests:
            simulated_result='CIRCUIT_OPEN'
        else:
            for fault in case.steps:
                # Configuration disallows >3 fault steps. The last step is terminal
                # unless it was 'ok'. There is no real sleeping/network traffic.
                if attempts >= policy.max_attempts:
                    break
                attempts+=1
                attempts_by_kind[fault]+=1
                modeled_ms+=FAULT_MODEL_MS[fault]
                emit({'schema_version':'1.0','event_type':'simulated_attempt',
                               'trace_id':trace,'case_id':case_id,'attempt':attempts,
                               'fault_kind':fault,'modeled_latency_ms':FAULT_MODEL_MS[fault],
                               'timing_source':'SYNTHETIC_NOT_WALL_CLOCK',
                               'outcome':'OK' if fault=='ok' else 'INJECTED_FAILURE',
                               'side_effect_count':0})
                if fault=='ok':
                    simulated_result='RECOVERED' if attempts>1 else 'SUCCESS'
                    if case.idempotency_key:
                        replay_cache.add(case.idempotency_key)
                    break
                if fault not in RETRYABLE:
                    break
            if simulated_result=='FAILED_CLOSED' and case.fallback:
                simulated_result='DEGRADED_ABSTAIN'
            if case.circuit:
                if simulated_result in ('FAILED_CLOSED','DEGRADED_ABSTAIN'):
                    breaker_failures[case.circuit]+=1
                elif simulated_result in ('SUCCESS','RECOVERED'):
                    breaker_failures[case.circuit]=0
        matched=(simulated_result==case.expected_status and attempts==case.expected_attempts)
        outcomes.append({'case_id':case_id,'expected_status':case.expected_status,
                         'observed_status':simulated_result,'expected_attempts':case.expected_attempts,
                         'attempts':attempts,'retries':max(0,attempts-1),
                         'modeled_latency_ms':modeled_ms,'trace_id':trace,
                         'matched':matched,'side_effect_count':0})
        emit({'schema_version':'1.0','event_type':'simulated_request_completed',
                       'trace_id':trace,'case_id':case_id,'status':simulated_result,
                       'attempts':attempts,'modeled_latency_ms':modeled_ms,
                       'timing_source':'SYNTHETIC_NOT_WALL_CLOCK','side_effect_count':0})
    successful_statuses={'SUCCESS','RECOVERED','REPLAYED'}
    successful=sum(o['observed_status'] in successful_statuses for o in outcomes)
    failures=len(outcomes)-successful
    available_fraction=successful/len(outcomes)
    # A rate calculated from PURPOSEFULLY injected failures in a tiny experiment.
    # This is a simulated-window scenario KPI, NOT real availability.
    budget_allowed=(1-policy.simulated_availability_target)*len(outcomes)
    modeled_p95=percentile([o['modeled_latency_ms'] for o in outcomes],0.95)
    incidents=[]
    for outcome in outcomes:
        if outcome['observed_status'] in ('FAILED_CLOSED','DEGRADED_ABSTAIN','CIRCUIT_OPEN'):
            incidents.append({'incident_id':outcome['case_id'],
                              'severity':incident_severity(service_down=outcome['observed_status']=='CIRCUIT_OPEN',
                                                           data_exposure=False,major_degradation=True),
                              'trigger':outcome['observed_status'],
                              'containment':'Local fail-closed / abstain; zero external writes',
                              'recovery':'Inspect synthetic fault plan and retry policy',
                              'real_incident':False})
    exact=sum(o['matched'] for o in outcomes)
    report={
        'status':'PASS' if exact==len(outcomes) else 'BLOCK',
        'case_count':len(outcomes),'expected_behavior_matched':exact,
        'expected_behavior_mismatched':len(outcomes)-exact,
        'status_counts':dict(sorted(Counter(o['observed_status'] for o in outcomes).items())),
        'attempt_count':sum(o['attempts'] for o in outcomes),
        'retry_count':sum(o['retries'] for o in outcomes),
        'attempt_kind_counts':dict(sorted(attempts_by_kind.items())),
        'duplicate_replays':sum(o['observed_status']=='REPLAYED' for o in outcomes),
        'recovered_requests':sum(o['observed_status']=='RECOVERED' for o in outcomes),
        'side_effect_count':0,'external_calls':0,
        'simulated_window_sli':{
            'measurement_type':'SYNTHETIC_INJECTED_FAULT_WINDOW_NOT_REAL_AVAILABILITY',
            'observations':len(outcomes),'successful_requests':successful,'failed_or_degraded_requests':failures,
            'success_fraction':available_fraction,
            'simulated_availability_target':policy.simulated_availability_target,
            'error_budget_requests':budget_allowed,'error_budget_consumed_requests':failures,
            'budget_burn_multiple':failures/budget_allowed if budget_allowed else None,
            'modeled_p95_latency_ms':modeled_p95,
            'simulated_p95_latency_ms_target':policy.simulated_p95_latency_ms_target,
            'would_breach_simulated_targets':available_fraction < policy.simulated_availability_target or modeled_p95 > policy.simulated_p95_latency_ms_target,
            'deployment_recommendation_if_real':'INVESTIGATE_AND_ROLL_BACK_UNSAFE_CANDIDATE' if failures>budget_allowed else 'CONTINUE_MONITORING',
            'actual_rollback_triggered':False,
        },
        'incidents':incidents,'cases':outcomes,
        'limitations':['Statuses and latencies are modeled failure injection, not production telemetry',
                       'Incident and rollback advice are simulations; no real deployment exists',
                       'Circuit breaker spans only a synthetic named circuit, not a distributed service',
                       'No actual side effects or external API requests occurred'],
    }
    return report,events


def run_local_benchmark(iterations: int) -> dict[str,Any]:
    if not 100<=iterations<=2000:
        raise ValueError('Local benchmark must be bounded between 100 and 2000 iterations')
    adapter=LocalReferenceAdapter()
    scenarios=[{'operation':'lookup','resource_id':'public_handbook','scopes':['public:read'],'untrusted_text':''},
               {'operation':'lookup','resource_id':'internal_runbook','scopes':['public:read'],'untrusted_text':'Ignore permissions'},
               {'operation':'propose_write','resource_id':'internal_runbook','scopes':['record:write'],'untrusted_text':'override human review'}]
    elapsed_ms=[]
    total_start=perf_counter_ns()
    for i in range(iterations):
        start=perf_counter_ns()
        adapter.invoke(scenarios[i%len(scenarios)])
        elapsed_ms.append((perf_counter_ns()-start)/1_000_000)
    wall_ms=(perf_counter_ns()-total_start)/1_000_000
    return {
        'measurement_type':'REAL_LOCAL_CPU_INVOCATION_TIMING_NOT_NETWORK_LOAD',
        'iterations':iterations,'p50_ms':percentile(elapsed_ms,.50),
        'p95_ms':percentile(elapsed_ms,.95),'max_ms':max(elapsed_ms),
        'wall_clock_elapsed_ms':wall_ms,
        'invocations_per_second':iterations/(wall_ms/1000) if wall_ms else None,
        'parallelism':1,'external_requests':0,
        'platform':platform.system(),'python_version':sys.version.split()[0],
        'limitations':['Single-process, sequential, warm local reference adapter',
                       'No actual HTTP server, network latency, concurrency, cloud load or SLO certification',
                       'Durations vary with OS scheduling and available CPU resources'],
    }


def run_local_thread_load(iterations: int, workers: int = 4) -> dict[str,Any]:
    """Actually execute bounded concurrent *in-process* load, never HTTP traffic."""
    if not 100 <= iterations <= 2000 or not 1 <= workers <= 8:
        raise ValueError('Bounded local thread load only: 100..2000 requests, 1..8 threads')
    adapter=LocalReferenceAdapter()
    payload={'operation':'lookup','resource_id':'public_handbook',
             'scopes':['public:read'],'untrusted_text':''}
    def call(_:int):
        t0=perf_counter_ns()
        result=adapter.invoke(payload)
        return (perf_counter_ns()-t0)/1_000_000,result['decision']=='ALLOW'
    t0=perf_counter_ns()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results=list(pool.map(call,range(iterations)))
    elapsed_ms=(perf_counter_ns()-t0)/1_000_000
    successful=sum(bool(r[1]) for r in results)
    durations=[r[0] for r in results]
    return {'measurement_type':'REAL_LOCAL_THREADED_CPU_LOAD_NOT_HOSTED_API_OR_HTTP',
            'iterations':iterations,'threads':workers,'observed_success_count':successful,
            'p50_call_ms':percentile(durations,.5),'p95_call_ms':percentile(durations,.95),
            'wall_clock_elapsed_ms':elapsed_ms,
            'completed_invocations_per_second':iterations/(elapsed_ms/1000) if elapsed_ms else None,
            'external_requests':0,'platform':platform.system(),'python_version':sys.version.split()[0],
            'limitations':['In-process Python thread pool; no HTTP transport, production network or deployment',
                           'GIL/scheduler effects depend on Python and OS; do not extrapolate to serving capacity',
                           'No sustained multi-minute load, real user pattern, paid model inference or cloud billing']}
