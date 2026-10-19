# Run from the Project 16 root. No API key or new install required.
$ErrorActionPreference = 'Stop'
$Python = Join-Path (Get-Location).Path '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Missing .venv\Scripts\python.exe. Reuse the CP1 environment.' }
if (-not (Test-Path -LiteralPath 'outputs\cp1_baseline_report.json')) { throw 'Missing CP1 report; run the CP1 CLI to generate it first.' }
$env:PYTHONPATH = (Resolve-Path .\src).Path
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'CP2 automated tests failed' }
& $Python -m ai_reliability.cli cp2 --output outputs/cp2_development_gate_report.json
if ($LASTEXITCODE -ne 0) { throw 'CP2 reference candidate should PASS but did not' }
& $Python -m ai_reliability.cli cp2 --variant unsafe_allow --output outputs/cp2_unsafe_allow_negative.json
if ($LASTEXITCODE -ne 1) { throw 'CP2 security regression should BLOCK (exit code 1)' }
& $Python -m ai_reliability.cli cp2 --variant overblock --output outputs/cp2_overblock_negative.json
if ($LASTEXITCODE -ne 1) { throw 'CP2 overblocking regression should BLOCK (exit code 1)' }
& $Python -m ai_reliability.cli cp2 --variant bad_citation --output outputs/cp2_bad_citation_negative.json
if ($LASTEXITCODE -ne 1) { throw 'CP2 grounding regression should BLOCK (exit code 1)' }
& $Python -m ai_reliability.cli cp2 --variant review_bypass --output outputs/cp2_review_bypass_negative.json
if ($LASTEXITCODE -ne 1) { throw 'CP2 approval-bypass regression should BLOCK (exit code 1)' }
Write-Host 'CP2 local validation succeeded: reference PASS and 4 injected-fault candidates BLOCK.'
