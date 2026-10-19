# CP4 — Offline validation, cross-project evidence bridge, and safe release gates

**Phase: CP4 Windows validation PASSED (118 tests, 0 skips); Git-index audit PASSED (96 paths / 0 findings); public repository published; initial-commit Ubuntu and Windows CI PASSED. Screenshot/documentation update and verification of CI on the final commit remain pending.**

## Evidence / tests

1. User Windows Python 3.12 run verified **118 passed and 0 skipped** (Oct 18, 2026).
2. Re-run the reference CP1/CP2/CP3 evaluations using *new* output paths under `outputs/cp4_replay/`. The four CP3 deliberately faulty variants must produce process code 1 / `BLOCK`, while reference PASS returns 0. All CP3 manifest files must verify with the existing checker.
3. Run repo candidate file audit (local-only). Confirm no `.env`, Python caches, outputs, executable binaries, secrets or private records are *candidates* for publication. This is a pattern scan and **cannot guarantee** absence of secrets.
4. The user Windows validation discovered and imported **actual read-only Project 15 audit metadata** from `../15_enterprise_ai_automation/artifacts/cp4_repository_audit.json`. The bridge validated the file contract; it is **not** a Project 15 runtime integration. Project 14 is not integrated.
5. Before public GitHub publication, `git add` only reviewed files and run `python scripts/release_audit.py --mode index --output outputs/cp4_index_audit.json` against *staged bytes*, inspect `git diff --cached --stat`, full diff, screenshots, `.gitignore`, and Git history; scan cannot certify images/history. Save report locally, not as a commit.
6. MIT license and public GitHub publication approved by user; screenshot filenames 01–06 saved and confirmed. **Do not commit or push until the real staged Git index and screenshot privacy are reviewed.** GitHub Actions will count as successful only when real hosted runs on the pushed commit succeed.

Windows validation from Project16 repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_cp4.ps1
```

Inputs: the prior CP3 Python venv and dependencies. No new dependencies, no Java/Hadoop/Spark, no real API key. Generated output stays gitignored. The script DOES NOT stage, commit, push, register a GitHub repository, or make external calls. It does not alter Project 15.

The CI workflow (`.github/workflows/quality-gates.yml`) runs on Ubuntu and Windows with Python 3.12, `pytest`, local evaluation/replay, real SHA-256 manifest check, and Git-index path + credential-pattern audit. The hosted Ubuntu and Windows jobs both passed on initial commit `7306971` (run `39185172801`, rerun #2). Verification on the screenshot/documentation update commit remains outstanding.

## Required upload after Windows run

- Terminal capture showing final `CP4 LOCAL PREPUBLICATION VALIDATION SUCCEEDED`.
- `outputs/cp4_replay/cp4_validation_summary.json`.
- `outputs/cp4_replay/candidate_audit.json`.
- If automatic Project 15 audit import runs: `outputs/cp4_replay/project15_actual_readonly.json`.
- If available, actual `15_enterprise_ai_automation/artifacts/cp4_repository_audit.json` for direct consistency review (inspect content for sensitive data first).

## Limitations and unresolved matters

- 20 CP3 security cases are fixed offline synthetic fixtures, **not** an independent held-out external evaluation or a real LLM red-team assessment.
- Actual Project 15 adapter only imports read-only metadata; it does **not** invoke Project 15's pipelines or APIs. The sample fixture is *not* real cross-project validation.
- Small fixed local tests and 400 in-process CPU operations are not production throughput, model safety, incident handling or statistical error estimates.
- No GDPR/SOC2/compliance certification or demographic fairness can be claimed.
- Hashes are unsigned and the reporter can rewrite reports and manifests.
- The CP4 candidate scan tests its own working tree, while the staged-index audit is explicitly separate. CI cannot establish successful GitHub execution without a real run.
- The staged Git-index audit, MIT/publication approval, repository creation, and first hosted CI pass are complete. Screenshot privacy must still be reviewed; verify CI again after the final screenshot/documentation commit.


## User-verified stage summary (October 18, 2026)

- `scripts/validate_cp4.ps1` completed with `CP4 LOCAL PREPUBLICATION VALIDATION SUCCEEDED`.
- 118/118 pytest tests passed, none skipped; candidate audit 87 candidate paths, zero findings.
- CP1/CP2/CP3 replay reference PASS, four intentionally unsafe variants BLOCK; all 10 CP3 manifests verified.
- Read-only real Project 15 CP4 audit metadata imported; not a service/runtime integration.
- Genuine Windows screenshots 01–06 saved by user in `screenshots/`.
- Local synthetic results do **not** represent independent red-team performance, production availability, real model safety, cloud deployment, security certification or real release approval.
- Completed subsequently: 96-path staged-index audit with zero findings; owner-approved MIT/public GitHub publication; commit `7306971`; passing hosted Ubuntu and Windows CI. Next: publish genuine screenshot files `07` and `08`, update documentation, and verify CI on the new pushed commit.
