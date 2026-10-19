"""Hard release blockers and cross-project report contract tests."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import pytest
from ai_reliability.cross_project import Project15EvidenceError, normalize_project15_cp4_audit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from release_audit import audit, check_path, check_text


def test_fixture_cross_project_contract_is_preliminary():
    result=normalize_project15_cp4_audit(ROOT/'data/fixtures/cp4_project15_audit_contract_sample.json')
    assert result['evaluation']=='PRELIMINARY_ONLY'
    assert result['writes_to_source']==0
    assert result['source_inspection_mode']=='candidate_files_without_git'

@pytest.mark.parametrize('alter',[
    {'schema_version':'cp3.audit.v1'},
    {'finding_count':1},
    {'code_audit_pass':False},
    {'inspection_mode':'production_attestation'},
    {'inspected_paths':-1},
    {'findings':[{'code':'BAD','path':'foo'}]},
    {'text_files_scanned':11},
])
def test_cross_project_fail_closed(tmp_path,alter):
    original=json.loads((ROOT/'data/fixtures/cp4_project15_audit_contract_sample.json').read_text())
    original.update(alter)
    f=tmp_path/'external.json'
    f.write_text(json.dumps(original))
    with pytest.raises(Project15EvidenceError):
        normalize_project15_cp4_audit(f)


def test_cross_project_blocks_real_findings(tmp_path):
    f=tmp_path/'actual.json'
    f.write_text(json.dumps({'schema_version':'cp4.audit.v1','inspection_mode':'git_index',
        'inspected_paths':5,'text_files_scanned':4,'finding_count':1,
        'findings':[{'path':'dummy','code':'POSSIBLE_SECRET_TOKEN'}],'code_audit_pass':False}))
    assert normalize_project15_cp4_audit(f)['evaluation']=='BLOCK'


def test_cross_project_staged_clean_report_is_only_local_pass(tmp_path):
    f=tmp_path/'actual.json'
    f.write_text(json.dumps({'schema_version':'cp4.audit.v1','inspection_mode':'git_index',
        'inspected_paths':5,'text_files_scanned':4,'finding_count':0,'findings':[],'code_audit_pass':True}))
    result=normalize_project15_cp4_audit(f)
    assert result['evaluation']=='PASS_LOCAL_STAGED_AUDIT'
    assert result['external_calls']==0


@pytest.mark.parametrize('name',[ '.env','project/.env','project/.env.local',
    '.venv/secrets.json','outputs/cp3_report.json','data/raw/person.json',
    'artifacts/staged.sqlite','docs/../private.txt','src/credentials.json',
    'src/script.exe','screenshots/random_image.png'])
def test_disallowed_staged_paths(name):
    assert check_path(name) is not None

@pytest.mark.parametrize('name',['.env.example','.github/workflows/quality-gates.yml',
    'src/ai_reliability/cli.py','screenshots/01_cp1_baseline.png','outputs/.gitkeep'])
def test_allowed_paths(name):
    assert check_path(name) is None


def test_secret_detection_redaction():
    assert check_text(b'OPENAI_API_KEY = something_real')=='POSSIBLE_SECRET_ASSIGNMENT'
    assert check_text(b'OPENAI_API_KEY = <YOUR_API_KEY>') is None
    assert check_text(b'OPENAI_API_KEY=') is None
    assert check_text(b'-----BEGIN ' + b'PRIVATE KEY-----')=='POSSIBLE_SECRET_TOKEN'


def test_local_candidate_audit_without_secrets(tmp_path):
    (tmp_path/'src').mkdir()
    (tmp_path/'src'/'safe.py').write_text("KEY_PLACEHOLDER = '<YOUR_API_KEY>'\n")
    (tmp_path/'outputs').mkdir()
    (tmp_path/'outputs'/'run.json').write_text('{"api_key":"fake"}')
    (tmp_path/'.env').write_text('OPENAI_API_KEY=DO_NOT_READ')
    result=audit(tmp_path,'candidate')
    assert result['code_audit_pass'] and result['inspected_paths']==1


def test_index_audit_reads_staged_blob_not_working_file(tmp_path):
    if subprocess.run(['git','--version'],capture_output=True).returncode != 0:
        pytest.skip('Git unavailable')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path/'file.py').write_text('OPENAI_API_KEY=real_secret_value\n')
    subprocess.run(['git','-C',str(tmp_path),'add','file.py'],check=True)
    (tmp_path/'file.py').write_text('# replaced working content\n')
    result=audit(tmp_path,'index')
    assert not result['code_audit_pass']
    assert result['findings'][0]['code']=='POSSIBLE_SECRET_ASSIGNMENT'
    assert result['inspection_mode']=='git_index'


def test_staged_secret_removed_does_not_falsely_fail(tmp_path):
    if subprocess.run(['git','--version'],capture_output=True).returncode != 0:
        pytest.skip('Git unavailable')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path/'file.py').write_text('# clean\n')
    subprocess.run(['git','-C',str(tmp_path),'add','file.py'],check=True)
    (tmp_path/'file.py').write_text('OPENAI_API_KEY=real_secret_value\n')
    result=audit(tmp_path,'index')
    assert result['code_audit_pass'] and result['text_files_scanned']==1


def test_reject_git_index_env(tmp_path):
    if subprocess.run(['git','--version'],capture_output=True).returncode != 0:
        pytest.skip('Git unavailable')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path/'.env').write_text('SECRET=secret\n')
    subprocess.run(['git','-C',str(tmp_path),'add','-f','.env'],check=True)
    result=audit(tmp_path,'index')
    assert not result['code_audit_pass']
    assert result['findings'][0]['code']=='PRIVATE_ENV'
