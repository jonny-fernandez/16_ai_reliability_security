"""Read-only candidate and real Git-index publication security-pattern scanner.

No secret bytes or sensitive source lines are printed to stdout or report.
The Git-index mode reads staged *blob* contents, not potentially different
working-tree files. A clean pattern scan is never a security guarantee.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

TEXT_SUFFIXES = {'.py','.ps1','.md','.txt','.toml','.json','.jsonl','.csv','.yml','.yaml','.gitattributes','.gitignore'}
BAD_SUFFIXES = {'.exe','.dll','.so','.dylib','.sqlite','.sqlite3','.db','.pkl','.pickle','.zip','.pem','.key','.pfx','.p12','.parquet','.env'}
SKIP_DIRS = {'.git','.venv','venv','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.idea','.vscode'}
PRIVATE_DIRS = {'outputs','logs','artifacts'}
ALLOWED_PLACEHOLDERS = {'outputs/.gitkeep','logs/.gitkeep','artifacts/.gitkeep','data/raw/.gitkeep','data/processed/.gitkeep','screenshots/.gitkeep'}
TOKEN_PATTERNS = [
    re.compile(r'(?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_-]{20,}'),
    re.compile(r'(?<![A-Za-z0-9])gh(?:p|o|u|s|r)_[A-Za-z0-9_]{28,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{20,}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
]
ASSIGNMENT = re.compile(r'^\s*["\']?([A-Z][A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY))["\']?\s*[:=]\s*(.*?)\s*,?\s*$',re.I)
PLACEHOLDER = ('<','${','YOUR_','EXAMPLE_','PLACEHOLDER','CHANGE_ME','INSERT_','DUMMY_','FAKE_','NONE','NULL','""',"''")


def check_path(name: str) -> str | None:
    if not name or '\\' in name or name.startswith('/') or any(s in {'','.','..'} for s in name.split('/')):
        return 'UNSAFE_PATH'
    parts = name.split('/')
    leaf = parts[-1]
    if leaf == '.env' or leaf.startswith('.env.') and leaf != '.env.example':
        return 'PRIVATE_ENV'
    if any(p in SKIP_DIRS for p in parts):
        return 'LOCAL_CACHE_OR_ENV'
    if (parts[0] in PRIVATE_DIRS or parts[:2] in (['data','raw'],['data','processed'])) and name not in ALLOWED_PLACEHOLDERS:
        return 'GENERATED_OR_PRIVATE_DATA'
    if leaf == '.gitkeep' and name not in ALLOWED_PLACEHOLDERS:
        return 'UNEXPECTED_PLACEHOLDER'
    if leaf in {'id_rsa','credentials.json','secrets.json'} or Path(leaf).suffix.lower() in BAD_SUFFIXES:
        return 'RESTRICTED_ARTIFACT'
    if parts[0] == 'screenshots' and leaf != '.gitkeep' and not re.fullmatch(r'\d{2}_[a-z0-9_-]+\.png',leaf,re.I):
        return 'UNAPPROVED_SCREENSHOT_NAME'
    if parts[0].startswith('.') and parts[0] not in {'.github','.gitignore','.gitattributes','.env.example'}:
        return 'UNEXPECTED_HIDDEN_FILE'
    return None


def check_text(content: bytes) -> str | None:
    try:
        value = content.decode('utf-8')
    except UnicodeError:
        return 'INVALID_UTF8'
    if any(p.search(value) for p in TOKEN_PATTERNS):
        return 'POSSIBLE_SECRET_TOKEN'
    for line in value.splitlines():
        stripped = line.strip()
        if stripped.startswith(('#','//','*','- ', '`', '"#')):
            continue
        m = ASSIGNMENT.match(line)
        if m:
            val = m.group(2).strip().rstrip(',').strip().strip('"\'').upper()
            if val and not val.startswith(PLACEHOLDER) and val not in {'ENV','TRUE','FALSE'}:
                return 'POSSIBLE_SECRET_ASSIGNMENT'
    return None


def candidate_entries(root: Path):
    for file in sorted(root.rglob('*')):
        if any(p in SKIP_DIRS for p in file.relative_to(root).parts):
            continue
        if not file.is_file() and not file.is_symlink():
            continue
        name = file.relative_to(root).as_posix()
        # Local, ignored outputs are not candidates for Git publication.
        if name in {'.env','.env.local'} or name.startswith('.env.') and name != '.env.example':
            continue
        if name.split('/')[0] in PRIVATE_DIRS and name not in ALLOWED_PLACEHOLDERS:
            continue
        if name.startswith(('data/raw/','data/processed/')) and name not in ALLOWED_PLACEHOLDERS:
            continue
        yield name, file, None


def index_entries(root: Path):
    proc = subprocess.run(['git','-C',str(root),'ls-files','--stage','-z'],capture_output=True)
    if proc.returncode:
        raise RuntimeError('git ls-files --stage failed or .git is absent')
    for item in proc.stdout.split(b'\0'):
        if not item: continue
        header, sep, name = item.partition(b'\t')
        if not sep or not header.startswith((b'100644 ',b'100755 ',b'120000 ',b'160000 ')):
            raise RuntimeError('Invalid Git stage entry')
        mode, objectid, stage = header.decode('ascii').split(' ')
        if stage != '0':
            raise RuntimeError('Unmerged Git index entry')
        yield name.decode('utf-8','strict'), None, (mode,objectid)


def audit(root:Path,mode:str)->dict:
    root=Path(root).resolve()
    if not root.is_dir(): raise ValueError('Invalid project root')
    findings=[]; paths=0; text_scanned=0
    iterator=candidate_entries(root) if mode=='candidate' else index_entries(root)
    for name, path, staged in iterator:
        paths+=1
        code=check_path(name)
        if code:
            findings.append({'path':name,'code':code});continue
        if staged:
            gitmode,oid=staged
            if gitmode not in {'100644','100755'}:
                findings.append({'path':name,'code':'UNSAFE_GIT_OBJECT_MODE'});continue
            proc=subprocess.run(['git','-C',str(root),'cat-file','blob',oid],capture_output=True)
            if proc.returncode:
                findings.append({'path':name,'code':'UNREADABLE_GIT_BLOB'});continue
            data=proc.stdout
        else:
            if path.is_symlink():
                findings.append({'path':name,'code':'SYMLINK_NOT_ALLOWED'});continue
            data=path.read_bytes()
        if len(data)>5_000_000:
            findings.append({'path':name,'code':'OVERSIZED_FILE'});continue
        if Path(name).suffix.lower() in TEXT_SUFFIXES or name=='.env.example' or name.endswith('.gitkeep'):
            code=check_text(data)
            text_scanned+=1
            if code: findings.append({'path':name,'code':code})
    return {'schema_version':'cp4.audit.v1','inspection_mode': 'git_index' if mode=='index' else 'candidate_without_git',
            'inspected_paths':paths,'text_files_scanned':text_scanned,'finding_count':len(findings),
            'findings':findings,'code_audit_pass':not findings,
            'limitations':['Pattern/path scan, not a full security audit or historical secret scan',
                           'Git-index mode audits staged BLOB bytes, not the current working-tree contents',
                           'Screenshots and previous Git history require independent manual review']}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--mode',choices=['candidate','index'],default='candidate')
    p.add_argument('--output',type=Path,default=Path('outputs/cp4_repository_audit.json'))
    a=p.parse_args()
    try:
        report=audit(a.root,a.mode)
        output=a.output if a.output.is_absolute() else a.root/a.output
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    except (OSError,ValueError,RuntimeError) as exc:
        print(f'CP4 audit ERROR: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
    print(f"CP4 audit: mode={report['inspection_mode']} paths={report['inspected_paths']} text={report['text_files_scanned']} findings={report['finding_count']}")
    for item in report['findings']:
        print(f"BLOCKED {item['path']}: {item['code']}")
    print(f'Report: {a.output}')
    return 0 if report['code_audit_pass'] else 1

if __name__=='__main__':
    raise SystemExit(main())
