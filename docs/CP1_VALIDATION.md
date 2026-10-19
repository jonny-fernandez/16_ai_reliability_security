# CP1 Windows validation and evidence

## Prerequisites

Python 3.11+ and a newly created project-specific virtual environment. Python 3.12 is suitable. This checkpoint needs only `pydantic` and `pytest`; **do not install all of `requirements.txt`** yet (those tools belong to later checkpoints). Nothing calls a paid API, connects to a cloud service, or uses `.env`.

## From PowerShell (run in the extracted `16_ai_reliability_security` directory)

```powershell
py -3.12 -m venv .venv
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
.\.venv\Scripts\python.exe -m pip install "pydantic>=2.8,<3" "pytest>=8.3,<10"
.\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
.\.venv\Scripts\python.exe -m ai_reliability.cli cp1 --output outputs/cp1_baseline_report.json
if ($LASTEXITCODE -ne 0) { throw "CP1 reference evaluation failed" }
Get-Content outputs\cp1_baseline_report.json | Select-String 'case_count|passed_count|failed_count|external_calls|consequential_writes'
```

If Python 3.12 is unavailable, choose an installed compatible Python via `py -0p`. Capture a clear screenshot showing the actual local pytest result and CLI output. Upload the screenshot and the generated report JSON for review. CP1 closes only after user-run evidence is reviewed.
