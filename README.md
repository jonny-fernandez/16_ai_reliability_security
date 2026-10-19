# Project 16 — AI Reliability, Governance, Security & Production Evaluation Platform

A production-oriented platform for evaluating entire AI systems under realistic quality, governance, security, load, and failure conditions.

Project 8 asked whether an AI output was acceptable. Project 16 asks whether a complete AI service can remain **correct, governed, secure, observable, recoverable, and deployable**.

## Main domains

- regression evaluation
- AI security / red teaming
- failure injection
- authorization testing
- model/data governance
- fairness/subgroup diagnostics
- lineage and reproducibility
- SLOs / SLIs / error budgets
- load/performance testing
- observability
- incident response
- deployment release gates


## CP1 local reference evaluator (development only)

A versioned, offline, synthetic reference assistant and exact-match evaluator have been added. Run `python -m ai_reliability.cli cp1 --output outputs/cp1_baseline_report.json` with Python 3.11+ and `pydantic` installed. See [`docs/CP1_VALIDATION.md`](docs/CP1_VALIDATION.md) for Windows commands and [`docs/CP1_EVALUATION_CONTRACT.md`](docs/CP1_EVALUATION_CONTRACT.md) for assumptions. The fixture checksum is verified before any evaluation. CP1 user Windows validation 10/10 scenarios and pytest green was reviewed on October 18, 2026; these results do not establish real LLM security, production performance, or release approval.

The deliverable includes only `.env.example`. Never copy a real `.env` into a ZIP or commit it.


## CP2 development release-gate simulation

CP2 adds offline baseline-versus-candidate evaluations, scenario-level error counts, false allow/block, groundedness, per-category diagnostics, governance model/data cards and SHA-256-based lineage evidence. It executes deliberately faulty local reference variants to prove BLOCK detection. Run `python -m ai_reliability.cli cp2` after generating CP1's baseline file. See [CP2 validation and limits](docs/CP2_VALIDATION.md). No provider credentials are used. CP2 is NOT production release approval, demographic fairness analysis, or live model safety proof.


## CP3 security, fault handling, and local observability (Windows-validated)

CP3 adds a new checksum-locked **20-case development** security suite, including legitimate utility despite hostile instructions; four negative faulty variants; **12 operational simulated-fault** cases with retries, idempotent replay, fail-closed behavior, circuit breaker and abstaining fallback; SHA-256 provenance; incident and simulated SLO metrics; structured JSONL; **actual in-memory OpenTelemetry SDK spans**; and CSV dashboard data. Separate **400-invocation sequential** and **400-invocation four-thread local in-process** benchmarks report actually observed machine runtime, but NOT network/HTTP/production load.

CP3 user Windows evidence was verified: **87 automated tests passed**, reference security **20/20** and operational faults **12/12** matched; four intended faulty candidates BLOCKED, and tampered evidence rejected. Uploaded reference report SHA-256 matched its uploaded manifest. This is offline development evidence, not real LLM security or production SLO compliance. See [CP3 validation](docs/CP3_VALIDATION.md).


## CP4 locally Windows-validated — publication and hosted CI pending

CP4 adds a read-only Project 15 **CP4 audit report** bridge, tested with synthetic contract fixtures and a read-only import of actual Project 15 audit metadata during the user Windows run. This is an evidence/report import, not a runtime integration with Project 15 services. It also adds a release security-pattern scanner that can inspect actual staged Git index blob contents, an offline CP1–CP3 replay and SHA-256 manifest verification, and Ubuntu/Windows GitHub Actions jobs that must be observed after publication before claiming success.

Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_cp4.ps1` in Windows PowerShell from repository root, reusing CP3 `.venv`. It installs nothing and never publishes. The candidate ZIP contains **`.env.example` only**, no actual `.env` or keys. No real LLMs, production services, cloud infrastructure, privacy attributes or paid APIs.

See [CP4 validation/release gates](docs/CP4_RELEASE_GATES.md), [prepublication screenshot and GitHub plan](docs/CP4_PUBLICATION_RUNBOOK.md), [checkpoint mapping](docs/CONSOLIDATED_CHECKPOINT_MAP.md), and [threat model](docs/THREAT_MODEL.md). On October 18, 2026, the user Windows CP4 gate passed: **118 tests passed, zero skipped**; the offline CP1/CP2/CP3 reference replay passed; four deliberately unsafe variants were correctly BLOCKED; 10 offline artifact manifests verified; and a **candidate-path** security scan inspected 87 paths with zero findings. Screenshots 01–06 were captured from genuine Windows evidence and saved by the user. The remaining publication gates are the **actual staged Git index** audit, independent screenshot review, public GitHub push, and genuine hosted Ubuntu/Windows CI verification. None of these local results authorize a real production release. A local candidate audit pass is NOT a staged Git-index audit, a full repository history/secret scan, real CI result, or production-release approval.


## Public repository and license

MIT license is approved for public GitHub publication. Publication is pending completion of an **actual staged-index audit** (not just the candidate-folder audit). Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stage_and_audit_cp4.ps1` before the first commit and review `outputs/cp4_index_audit.json`, `git diff --cached --stat`, `git diff --cached --check` and all six screenshot images. The staged-index script never commits, pushes or creates a GitHub repository. Do not commit generated `outputs/` or local `.env` files. Only `.env.example` belongs in the repository.

Hosted GitHub CI has not yet been observed. Screenshots `07_github_ubuntu_ci.png` and `08_github_windows_ci.png` must come from successful actual jobs on the published commit; do not manufacture them.
