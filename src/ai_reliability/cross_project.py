"""Read-only, schema-specific Project 15 CP4 audit ingestion.

This is a *contract* bridge.  A synthetic fixture tests it; an actual Project 15
report must be supplied and verified separately before claiming cross-project
execution. Never imports or invokes Project 15 code or API credentials.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

ALLOWED_MODES = {'git_index', 'candidate_files_without_git'}

class Project15EvidenceError(ValueError):
    pass


def normalize_project15_cp4_audit(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
        raise Project15EvidenceError('Invalid source: expected bounded, ordinary JSON report')
    raw = path.read_bytes()
    try:
        artifact = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError) as exc:
        raise Project15EvidenceError('Unreadable Project 15 audit JSON') from exc
    if not isinstance(artifact, dict) or artifact.get('schema_version') != 'cp4.audit.v1':
        raise Project15EvidenceError('Project 15 CP4 audit schema mismatch')
    mode = artifact.get('inspection_mode')
    if mode not in ALLOWED_MODES:
        raise Project15EvidenceError('Unrecognized Project 15 inspection mode')
    scan = artifact.get('text_files_scanned')
    inspected = artifact.get('inspected_paths')
    issues = artifact.get('findings')
    issue_count = artifact.get('finding_count')
    clean = artifact.get('code_audit_pass')
    if any(type(i) is not int or i < 0 for i in (scan, inspected, issue_count)):
        raise Project15EvidenceError('Invalid audit counts')
    if scanned_invalid := (scan > inspected):
        raise Project15EvidenceError('More scanned text files than indexed paths')
    if not isinstance(issues, list) or len(issues) != issue_count or type(clean) is not bool:
        raise Project15EvidenceError('Inconsistent findings or audit decision')
    if any(not isinstance(x, dict) or not isinstance(x.get('code'),str) or not isinstance(x.get('path'),str) for x in issues):
        raise Project15EvidenceError('Malformed finding metadata')
    if clean != (issue_count == 0):
        raise Project15EvidenceError('Inconsistent success/finding fields')
    # Candidate-file success is only preliminary. An actual staged-index scan is
    # required before publication and is never inferred from a candidate scan.
    status = 'PASS_LOCAL_STAGED_AUDIT' if clean and mode == 'git_index' else ('PRELIMINARY_ONLY' if clean else 'BLOCK')
    return {
        'schema_version': 'cp4.project15.audit.bridge.v1',
        'producer': 'project15_local_cp4_audit',
        'input_sha256': hashlib.sha256(raw).hexdigest(),
        'source_inspection_mode': mode,
        'source_paths_scanned': inspected,
        'source_text_files_scanned': scan,
        'source_finding_count': issue_count,
        'source_finding_codes': sorted({x['code'] for x in issues}),
        'evaluation': status,
        'external_calls': 0,
        'writes_to_source': 0,
        'limitations': [
            'Source audit may be synthetically authored or stale; its provenance is not independently attested.',
            'No Project 15 runtime, queue, Spark, deployment, or CI is executed through this bridge.',
            'Staged-index source results do not replace Project 16 staging, secret or screenshot review.',
        ],
    }
