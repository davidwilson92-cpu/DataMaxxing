"""Verify the owner-authorised, exact-scope beta. Not commercial certification."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def files(root):
    found=set()
    for folder in ('nova','scripts','tests','.github'):
        found.update(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    found.update(p for p in root.iterdir() if p.is_file() and (p.suffix in {'.py','.ini','.yaml','.toml','.txt'} or p.name in {'Dockerfile','.dockerignore','AGENTS.md'}))
    found.update(root/p for p in ('docs/beta/KNOWN_GAPS.md','docs/beta/deferred-register.json'))
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in found}

def validate(root=ROOT):
    manifest=json.loads((root/'docs/beta/release-scope.json').read_text(encoding='utf-8'))
    if manifest.get('release_class')!='limited-beta' or manifest.get('authorised_on')!='2026-10-10':
        raise ValueError('Missing scoped beta authorisation')
    if manifest.get('commercial_ready') is not False:
        raise ValueError('Beta must not claim commercial readiness')
    if files(root)!=manifest['files']:
        raise ValueError('Candidate changed: review scope and rerun required validation')
    register=json.loads((root/'docs/beta/deferred-register.json').read_text(encoding='utf-8'))
    if {r['id'] for r in register['sections']}!=set(range(1,80)):
        raise ValueError('Known-gap register is incomplete')
    return 'LIMITED BETA scope verified; commercial readiness remains unapproved'

if __name__=='__main__':
    print(validate())
