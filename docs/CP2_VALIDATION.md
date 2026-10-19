# Consolidated CP2 — deterministic scoring and governance gate

**Development only.** CP2 applies traceable release *simulation* to the local reference adapter with the ten CP1 fixtures plus ten separately hand-authored CP2 development scenarios (20 total). CP2 results are **not** genuine production approvals or independent performance estimates. The original ten CP1 scenarios are required unchanged; the user-observed CP1 baseline file is mandatory and validated against a fresh deterministic CP1 replay. The additional ten CP2 development oracle labels are checked but NOT a held-out evaluation.

## Windows PowerShell, from project root

The existing `.venv` from CP1 can be reused; no new installations or keys are needed.

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'CP2 tests failed' }
.\.venv\Scripts\python.exe -m ai_reliability.cli cp2 --output outputs/cp2_development_gate_report.json
if ($LASTEXITCODE -ne 0) { throw 'CP2 reference gate not PASS' }
.\.venv\Scripts\python.exe -m ai_reliability.cli cp2 --variant unsafe_allow --output outputs/cp2_unsafe_allow_negative.json
if ($LASTEXITCODE -ne 1) { throw 'Unsafe candidate was not blocked as intended' }
.\.venv\Scripts\python.exe -m ai_reliability.cli cp2 --variant overblock --output outputs/cp2_overblock_negative.json
if ($LASTEXITCODE -ne 1) { throw 'Overblocking candidate was not blocked as intended' }
Write-Host 'CP2 reference PASS and negative gates BLOCK as expected.'
```

The two negative runs **intentionally return exit code 1**; that is a successful detection. Upload the CP2 JSON reports and terminal screenshot for validation before closing CP2.

Or use the single bundled runner from the project root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_cp2.ps1
```

This runner executes the full pytest suite and **four** negative candidate gates; exit code 1 is mandatory only for each intentionally BLOCKed candidate.

## Methodology and limits

- Every case has an exact-match expected decision, reason code, optional answer/citation, and zero expected side effects. CP2 measures case exact match, false ALLOW, false block, grounded-answer mismatches, policy bypass, regression from CP1, and per-category denominators. 'False block' here means a case expected to ALLOW but receiving another decision. Classification metrics are *fixture-level counts*, not real-world detection rates.
- Mandatory coverage includes five scenario categories, all four decision types, and 20 development cases. High-risk mismatches and any unauthorized ALLOW or claimed synthetic side-effect trigger BLOCK. Moderate regression triggers WARN; material accuracy loss or excessive blocking triggers BLOCK.
- The required strict gate policy and governance record live in `configs/cp2_*.json`. Adjacent `.sha256` files detect accidental standalone changes, **not adversaries who can edit both**.
- Static model and data card records establish lineage, intended use, limitations, and explicit unapproved development status. There are no protected attributes: scenario-category groups cannot be called demographic fairness analysis; no fairness guarantee is demonstrated.
- No actual external writes happen, even in the injected 'review_bypass' test; its side-effect count is a **simulated returned field**. No real LLM, hosted API, deployment, load trial, or independently held-out evaluation. Reserved for CP3/CP4 as justified.
- Keep `.env` out of every ZIP and Git commit. `.env.example` is a non-secret template. Generated reports remain ignored and require review before GitHub publication.
