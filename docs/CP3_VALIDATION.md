# Consolidated CP3 — adversarial security, injected reliability, tracing and evidence

**Status: User Windows validation and JSON report review completed October 18, 2026 (87 tests passing; reference 20/20 security, 12/12 operational; four faulty candidates blocked; tampered manifest rejected).** The locally authored fixtures are locked by stored SHA-256 checksums at this checkpoint; the tests are **development simulations**, not an external blind holdout or an assurance of real-world model security. CP3 does not use a real LLM, hosted integration, production incident, or network calls.

## Windows PowerShell

From the existing `16_ai_reliability_security` directory, after extracting the CP3 full replacement ZIP over the existing source:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-cp3.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_cp3.ps1
```

The script requires the **unchanged** observed CP1 report (`outputs/cp1_baseline_report.json`) and observed CP2 reference report (`outputs/cp2_development_gate_report.json`). It replay-validates both before CP3. It runs pytest, CP3 reference, the four deliberately broken candidate variations, SHA-256 verification, and deliberate tampering of a disposable COPY. Exits `1` for faulty candidates and `2` for deliberately corrupted evidence are **intended**; the overall script must exit `0`.

Capture the **actual terminal** when the final validation summary appears. Upload:

- `outputs/cp3_reference/cp3_report.json`
- `outputs/cp3_reference/cp3_manifest.json`
- `outputs/cp3_unsafe_allow/cp3_report.json`
- `outputs/cp3_review_bypass/cp3_report.json`
- Terminal screenshot (do not publish yet; final screenshot filenames are assigned during CP4).

## Scope and methodology

1. **Security:** exactly 20 new locked synthetic scenario oracles, distinct by case ID from CP2; expected decisions: ALLOW 5, DENY 11, REVIEW 2, ABSTAIN 2. Categories: legitimate 2, authorization 8, injection 6, approval 2, unknown resources 2. Includes prompt-injection strings, scope spoofing, indirect-like retrieval instructions placed as untrusted user input, response-grounding integrity, faux exfiltration requests, elevated actions, and legitimate utility under hostile text. Note: the local reference adapter deliberately **ignores** all untrusted text; these are authorization-boundary regressions, NOT a real RAG or model prompt-injection assessment.
2. **Release-gate simulation:** compares against reference-oracle behavior with the strict versioned CP3 policy. Blocked candidates simulate unauthorized disclosure, overblocking, invalid citations and human review bypass. Side effect counts in adversarial variants are **returned synthetic fields**, never external side effects. A reference `PASS` means **development test acceptance only**.
3. **Failure handling:** 12 distinct synthetic operation-level tests with a maximum of three modeled attempts, retryable timeout/429 failures, terminal malformed/auth failures, abstaining fallback, idempotent replay, and a bounded circuit breaker. Counts separate attempts from requests, retries, recovered requests, no-attempt replays and circuit refusals. There are zero external writes.
4. **Simulated SLOs:** a fixed synthetic fault-heavy window uses a 95% modeled availability target and 250 ms modeled p95 target, and computes error budget consumption explicitly. Its failure percentage is deliberately adversarial sampling, not production availability. A simulated breach **does not** fail the test harness when correct containment is demonstrated. The suggested rollback is advisory only and does not modify any deployment.
5. **Actually measured speed:** separate sequential local CPU benchmark invokes the deterministic adapter 400 times and measures real Python `perf_counter_ns()` durations. Report includes measured p50, p95 and throughput, with OS/Python metadata. Separately, a real bounded **four-thread local in-process load** performs another 400 invocations and reports measured p50/p95 and throughput. Neither is HTTP/Locust traffic, network load or production latency. Avoid environment-independent performance thresholds.
6. **OpenTelemetry:** genuine OpenTelemetry SDK spans are captured with an in-memory exporter and sanitized attributes. The SDK spans measure local processing; injected timeout latencies in the JSONL event log are synthetic data fields, *not* span durations. No OTLP collector, public exporter or network transmission. Span and event counts reconcile to the dashboard dataset.
7. **Evidence:** `cp3_report.json`, `cp3_events.jsonl`, `cp3_spans.jsonl` and `cp3_dashboard.csv` are cross-hashed in a fixed-filename `cp3_manifest.json`. An integrity check fails if any covered file is changed or absent. These are UNSIGNED local hashes, not adversary-proof, not nonrepudiation and not protection against an attacker who controls both data and manifest.

## Incident model and limitations

Simulated failures generate severity, containment and proposed recovery records. Neither the synthetic incident count nor modeled SLO violation is observed production telemetry. Do not claim tested production load, live rollback, regulated compliance certification, fairness results, robust model jailbreak resistance or actual service-availability performance from this evidence. See `docs/INCIDENT_RESPONSE.md`, `docs/SERVICE_LEVEL_OBJECTIVES.md`, and `docs/THREAT_MODEL.md`.

CP4 remains responsible for cross-platform CI on a *pushed commit*, real integration adapter to Projects 14/15, security/staging audit, screenshot Word handoff, explicit GitHub approval, and final resume update.
