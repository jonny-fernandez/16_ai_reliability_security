"""CLI to import a user-selected real Project 15 CP4 audit report, read only."""
import argparse
import json
from pathlib import Path
from ai_reliability.cross_project import normalize_project15_cp4_audit, Project15EvidenceError


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,type=Path,help='Actual Project 15 artifacts/cp4_repository_audit.json')
    p.add_argument('--output',default='outputs/cp4_project15_bridge.json',type=Path)
    a=p.parse_args()
    try:
        result=normalize_project15_cp4_audit(a.source)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    except (OSError, ValueError, Project15EvidenceError) as exc:
        print(f'CP4 bridge ERROR: {type(exc).__name__}: {exc}')
        return 2
    print(f"Project15 bridge: source={result['source_inspection_mode']} findings={result['source_finding_count']} status={result['evaluation']}")
    print('This is read-only Project 15 audit metadata, not Project 15 runtime integration.')
    return 1 if result['evaluation']=='BLOCK' else 0

if __name__=='__main__':raise SystemExit(main())
