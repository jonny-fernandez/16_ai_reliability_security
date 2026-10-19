# SLO and SLI definitions — development only

Two **non-interchangeable** sources of timing/availability information:

| Source | Unit | Role | Prohibited conclusion |
|---|---|---|---|
| Synthetic fault-injection cases | 12 artificial requests, 20 attempted calls | Test fail-closed, retries, fallback, circuit and simulated budget | Cannot estimate uptime or latency of an actual service |
| Local CPU `perf_counter_ns()` benchmark | 400 sequential Python adapter invocations | Machine-observed local processing time with p50/p95 | Not a network, cost or production load benchmark |
| Local four-thread load | 400 in-process Python invocations | Measured bounded threaded processing throughput, p50/p95 | Not HTTP/Locust, real user concurrency or serving capacity |

Simulation policy in `configs/cp3_ops_policy.json`: modeled **availability 95%**, modeled **p95 <= 250 ms**, three maximum attempts, two terminal failed requests before breaker opens. Example permitted error budget is `n * (1 - 0.95)` requests across the intentionally fault-heavy window. Fractional budgets reflect arithmetic, NOT a realistic 12-request SLO monitoring period. The sample explicitly includes deliberately injected outages; a warning/recommendation is diagnostic only. Recovery rate is `recovered_requests / requests_with_retryable_failures`, with denominator disclosed rather than extrapolated.

When implementing actual production monitoring in a future project, define a representative population, duration, service-level failure conventions, real monotonic measurements, sustained burn-rate windows, alert routing, missing telemetry handling, and permissioned remediation before setting an enforceable production SLO. None exist in CP3.
