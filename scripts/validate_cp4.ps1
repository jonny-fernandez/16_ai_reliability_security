# Project 16 CP4 local Windows test + replay gate. NO Git writes or network calls.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $Root
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Missing CP3-passing .venv; do not use global Python.' }
$env:PYTHONPATH = Join-Path $Root 'src'
Write-Host 'CP4: checking dependencies and running full Windows tests...'
& $Python -c 'from opentelemetry.sdk.trace import TracerProvider; import pydantic, pytest'
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies incomplete.' }
$JUnit = Join-Path $env:TEMP ("project16_cp4_" + [guid]::NewGuid().ToString('N') + '.xml')
try {
    & $Python -m pytest -q -o addopts= --junitxml=$JUnit
    if ($LASTEXITCODE -ne 0) { throw 'CP4 Python tests failed.' }
    [xml]$Doc = Get-Content -LiteralPath $JUnit -Raw
    $Suites = @($Doc.testsuites.testsuite)
    $TotalTests = 0; $Skipped = 0; $Failures = 0
    foreach ($Suite in $Suites) {
        $TotalTests += [int]$Suite.tests
        $Skipped += [int]$Suite.skipped
        $Failures += [int]$Suite.failures + [int]$Suite.errors
    }
    if ($Skipped -ne 0 -or $Failures -ne 0 -or $TotalTests -lt 87) {
        throw "Incomplete Windows gate: tests=$TotalTests skipped=$Skipped errors_or_failures=$Failures"
    }
    Write-Host "CP4: pytest $TotalTests passed, 0 skips."
} finally {
    Remove-Item -LiteralPath $JUnit -Force -ErrorAction SilentlyContinue
}
Write-Host 'CP4: running offline CP1/CP2/CP3 replay, tamper-manifest verification and candidate audit...'
$Project15 = Join-Path (Split-Path $Root -Parent) '15_enterprise_ai_automation\artifacts\cp4_repository_audit.json'
if (Test-Path -LiteralPath $Project15) {
    Write-Host 'CP4: actual Project 15 CP4 audit file found. Importing read-only metadata.'
    & $Python .\scripts\validate_cp4.py --project15-audit $Project15
} else {
    Write-Host 'CP4: actual Project 15 audit file not found. Cross-project real export still pending.'
    & $Python .\scripts\validate_cp4.py
}
if ($LASTEXITCODE -ne 0) { throw 'CP4 replay/audit failed.' }
Write-Host 'CP4 LOCAL PREPUBLICATION VALIDATION SUCCEEDED. No GitHub publication performed.'
Write-Host 'Upload terminal screenshot + outputs/cp4_replay/cp4_validation_summary.json + outputs/cp4_replay/candidate_audit.json.'
