# Consolidated CP3 offline validation. Run from Project 16 repository root.
# Deliberately broken candidates return exit code 1; this is EXPECTED.
$ErrorActionPreference = 'Stop'
$Python = Join-Path (Get-Location).Path '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Missing .venv. Reuse CP1/CP2 Python environment.' }
if (-not (Test-Path -LiteralPath 'outputs\cp1_baseline_report.json')) { throw 'CP1 report missing. Preserve original validated output.' }
if (-not (Test-Path -LiteralPath 'outputs\cp2_development_gate_report.json')) { throw 'CP2 report missing. Preserve original validated output.' }
$env:PYTHONPATH = (Resolve-Path '.\src').Path
Write-Host 'CP3: Checking Python dependencies and running pytest suite...'
& $Python -c 'from opentelemetry.sdk.trace import TracerProvider; import pydantic, pytest'
if ($LASTEXITCODE -ne 0) { throw 'CP3 packages missing. Run .\.venv\Scripts\python.exe -m pip install -r requirements-cp3.txt' }
Write-Host 'CP3 core Python dependencies OK.'
& $Python -m pytest -q -o addopts=
if ($LASTEXITCODE -ne 0) { throw 'CP3 tests failed. Do not proceed.' }
Write-Host 'CP3: Evaluating reference security and operational scenarios...'
& $Python -m ai_reliability.cli cp3 --output-dir outputs/cp3_reference
if ($LASTEXITCODE -ne 0) { throw 'CP3 reference failed. Do not proceed.' }
& $Python -m ai_reliability.cli cp3-verify --output-dir outputs/cp3_reference
if ($LASTEXITCODE -ne 0) { throw 'CP3 reference evidence manifest failed.' }
$Variants = @('unsafe_allow', 'overblock', 'bad_citation', 'review_bypass')
foreach ($Variant in $Variants) {
  $Path = "outputs/cp3_$Variant"
  & $Python -m ai_reliability.cli cp3 --variant $Variant --output-dir $Path
  if ($LASTEXITCODE -ne 1) { throw "CP3 injected fault $Variant should BLOCK (exit code 1)" }
  & $Python -m ai_reliability.cli cp3-verify --output-dir $Path
  if ($LASTEXITCODE -ne 0) { throw "CP3 $Variant artifact integrity failed" }
}
Write-Host 'CP3: Confirming that a modified evidence file is rejected...'
$TamperFolder = 'outputs\cp3_tamper_negative'
if (Test-Path -LiteralPath $TamperFolder) { Remove-Item -LiteralPath $TamperFolder -Recurse -Force }
Copy-Item -LiteralPath 'outputs\cp3_reference' -Destination $TamperFolder -Recurse
try {
  Add-Content -LiteralPath "$TamperFolder\cp3_dashboard.csv" -Value 'SIMULATED_TAMPER' -Encoding UTF8
  & $Python -m ai_reliability.cli cp3-verify --output-dir $TamperFolder
  if ($LASTEXITCODE -ne 2) { throw 'Tampered evidence was NOT rejected (expected integrity exit code 2)' }
  Write-Host 'CP3 injected integrity corruption was rejected as expected.'
} finally {
  if (Test-Path -LiteralPath $TamperFolder) { Remove-Item -LiteralPath $TamperFolder -Recurse -Force }
}
Write-Host 'CP3 local validation succeeded: reference PASS, 4 fault candidates BLOCK, tampered manifest evidence rejected.'
Write-Host 'Capture terminal screenshot now and upload outputs/cp3_reference/cp3_report.json + outputs/cp3_reference/cp3_manifest.json, plus unsafe_allow/review_bypass cp3_report.json.'
Write-Host 'This is not production release approval or real availability evidence.'
exit 0
