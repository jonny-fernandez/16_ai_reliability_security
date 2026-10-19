# Project 16 — prepublication workflow and screenshots (DO NOT PUBLISH YET)

## Stage A — Before any GitHub repository creation

1. Run `scripts/validate_cp4.ps1` and send evidence/report files. Reconcile tests, failures and candidate scan. If Project 15 report is missing, provide it or mark real bridge evaluation as pending; do not claim it was exercised.
2. Use the existing Windows terminal screenshots and the CP4 evidence to prepare **six genuine prepublication PNGs**, no generated/faked CLI/CI status screenshots. Capture clean and privacy reviewed terminal views. Proposed names:

| File in `screenshots/` | What it must demonstrate | When |
| --- | --- | --- |
| `01_cp1_baseline.png` | Original CP1 Windows reference evaluation and test pass | Existing real evidence, after privacy check |
| `02_cp2_reference_gate.png` | Original CP2 20/20 reference PASS | Existing real evidence |
| `03_cp2_negative_gates.png` | Four deliberately faulty CP2 candidates BLOCK | Existing real evidence |
| `04_cp3_security_reliability.png` | CP3 Windows 87 green tests, reference PASS and fault BLOCK | Existing real evidence, clean crop/recapture if needed |
| `05_cp3_integrity_telemetry.png` | CP3 tampering rejection + manifest/observability lines | Existing real evidence, clean crop/recapture if needed |
| `06_cp4_windows_audit.png` | Full CP4 tests plus candidate file audit 0 findings | After Windows CP4 gate passes |

3. **Before GitHub**, assistant prepares a Word document embedding the six actual PNG files with exact names, notes and what each proves. User confirms saving the originals in `screenshots/`. No screenshot may show actual credentials, private paths not approved for public use, proprietary business information or fabricated success.
4. Confirm license (MIT is proposed, not authorized by earlier Project 15 license). Confirm actual GitHub publication and repository name separately.

## Stage B — Only AFTER screenshot confirmation + explicit GitHub authorization

User stages reviewed paths only, audits staged Git **blob** bytes (not just local candidate files), reviews full staged diff, confirms no `.env`, secrets, screenshots with private data or unwanted binaries. Do not stage generated `outputs/`, `.venv/`, or external project folders.

```powershell
# ONLY at the publication checkpoint after explicit confirmation:
.\.venv\Scripts\python.exe .\scripts\release_audit.py --mode index --output outputs/cp4_index_audit.json
if ($LASTEXITCODE -ne 0) { throw 'Do not commit: staged-index audit failed' }
git diff --cached --stat
git diff --cached --check
```

Any new screenshots or commits after that audit require a fresh staged-index audit. A 0-findings result does not exclude secrets in screenshots, previous commits, or other sources.

## Stage C — After actual successful push and hosted CI

- `07_github_ubuntu_ci.png` — genuine successful Ubuntu job in GitHub Actions for correct commit.
- `08_github_windows_ci.png` — genuine successful Windows job in GitHub Actions for correct commit.

If CI fails, fix, rerun, and update claims. Add those original PNGs and update the Word handoff and README only after real verification. Never assert that a future README-only commit's CI passed unless it did.

Update `Jonnathan_Fernandez_Offline_Master_Resume.docx` *after* publication using only validated counts, with no invented real-world production or business metrics; preserve all previous projects and original style.
