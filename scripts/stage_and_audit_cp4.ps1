# Project 16 - safe, allowlist-only Git staging + staged BLOB scanner.
# Stops before commit/push. Run from any working directory on Windows PowerShell.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Missing local .venv Python; run from validated Project 16 folder' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is not installed/on PATH' }
$expected = @(Get-Content -LiteralPath '.\scripts\publication_allowlist.txt' | Where-Object { $_ -and -not $_.StartsWith('#') })
if ($expected.Count -lt 85) { throw 'Allowlist incomplete' }
foreach ($name in $expected) {
    if ($name -match '[\\]' -or $name -match '(^/|\.\.|^[a-zA-Z]:)') { throw "Unsafe allowlist path: $name" }
    if (-not (Test-Path -LiteralPath $name -PathType Leaf)) { throw "Missing reviewed publication file: $name" }
}
# Exactly the six approved local prepublication screenshots (CI screenshots come later).
$expectedShots = @('01_cp1_baseline.png','02_cp2_reference_gate.png','03_cp2_negative_gates.png',
 '04_cp3_security_reliability.png','05_cp3_integrity_telemetry.png','06_cp4_windows_audit.png')
$shots = @(Get-ChildItem -LiteralPath .\screenshots -Filter *.png -File | Select-Object -ExpandProperty Name | Sort-Object)
$diffShots = @(Compare-Object -ReferenceObject ($expectedShots | Sort-Object) -DifferenceObject $shots)
if ($diffShots.Count -gt 0) { throw 'Screenshot folder does not have exactly the 6 reviewed prepublication PNGs' }
# Do not let pre-existing, unreviewed Git-index entries silently through.
if (-not (Test-Path -LiteralPath '.git')) {
    git init -b main | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Git initialization failed' }
}
# Stage only the fixed allowed paths. We check *all* staged paths, including any pre-existing entries.
git add -- $expected
if ($LASTEXITCODE -ne 0) { throw 'Git add failed' }
$stagedRaw = git diff --cached --name-only
if ($LASTEXITCODE -ne 0) { throw 'Cannot list staged paths' }
$staged = @($stagedRaw | Where-Object { $_ })
$extra = @($staged | Where-Object { $_ -notin $expected })
if ($extra.Count -gt 0) {
    Write-Host 'Unexpected staged files:' -ForegroundColor Red
    $extra | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    throw 'Unreviewed staged files present; unstage them, then re-run audit'
}
if ($staged.Count -lt 85) { throw 'Too few files staged for an initial commit; inspect Git status before continuing' }
# This is an actual BLOB/INDEX byte scan, not a candidate-path scan.
& $python .\scripts\release_audit.py --mode index --output outputs/cp4_index_audit.json
if ($LASTEXITCODE -ne 0) { throw 'Staged-index security audit failed; do NOT commit/push' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Staged diff contains whitespace/errors; do NOT commit/push' }
Write-Host ''
Write-Host 'STAGED DIFF SUMMARY (no commit/push yet)' -ForegroundColor Cyan
git diff --cached --stat
if ($LASTEXITCODE -ne 0) { throw 'Cannot summarize staged diff' }
Write-Host ''
Write-Host 'SCREENSHOT SHA256 VALUES; manually open each PNG and verify no secrets/PII before publication:' -ForegroundColor Yellow
Get-ChildItem -LiteralPath .\screenshots -File -Filter *.png | Sort-Object Name | ForEach-Object {
    $hash=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    Write-Host "$($_.Name)  $hash"
}
Write-Host ''
Write-Host 'CP4 STAGING AUDIT COMPLETE -- ZERO COMMIT/PUSH ACTIONS PERFORMED' -ForegroundColor Green
Write-Host 'Send the terminal summary and outputs/cp4_index_audit.json for review.'
