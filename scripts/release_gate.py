"""Fail-closed production assessment. No network, secrets, or app imports.

--check validates the register; default execution decides production readiness.
Code/test success cannot automatically attest infrastructure or human reviews.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTER = 'docs/guardrails/assessment.json'
BASELINE = 'docs/PRODUCTION_GUARDRAILS.md'


def digest(path):
    # Stable between Windows checkout and Linux build.
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def source_digest(root=ROOT):
    paths = set()
    for folder in ('nova', 'scripts', 'tests', '.github'):
        paths.update(p for p in (root / folder).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    paths.update(p for p in root.iterdir() if p.is_file() and
                 (p.suffix in {'.py', '.ini', '.yaml', '.toml', '.txt'} or
                  p.name in {'Dockerfile', '.dockerignore'}))
    value = '\n'.join(f'{p.relative_to(root).as_posix()}:{digest(p)}' for p in sorted(paths, key=lambda p: p.relative_to(root).as_posix()))
    return hashlib.sha256(value.encode()).hexdigest()


def validate(data, root=ROOT, release=True):
    errors = []
    baseline = root / BASELINE
    titles = dict((int(i), title.strip()) for i, title in re.findall(r'^# (\d+)\. (.+)$', baseline.read_text(encoding='utf-8'), re.M))
    if data.get('schema_version') != 1:
        errors.append('Unsupported assessment schema')
    if len(titles) != 79 or data.get('baseline_sha256') != digest(baseline):
        errors.append('Guardrail baseline is missing, altered, or unreviewed')
    rows = data.get('sections', [])
    if not isinstance(rows, list):
        return errors + ['sections must be a list']
    ids = [r.get('id') for r in rows if isinstance(r, dict)]
    if len(ids) != len(rows) or len(ids) != 79 or set(ids) != set(titles):
        errors.append('Exactly one assessment of every section 1–79 is required')
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = f"Section {row.get('id')}"
        if row.get('title') != titles.get(row.get('id')):
            errors.append(f'{label}: title does not match the baseline')
        state = row.get('status')
        if state not in {'met', 'partial', 'gap', 'unverified', 'not_applicable'}:
            errors.append(f'{label}: invalid status')
        if row.get('severity') not in {'P0', 'P1', 'P2', 'P3'}:
            errors.append(f'{label}: invalid severity')
        for field in ('owner', 'finding', 'next_action'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f'{label}: missing {field}')
        evidence = row.get('evidence', [])
        if not isinstance(evidence, list):
            errors.append(f'{label}: evidence must be a list')
            evidence = []
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                errors.append(f'{label}: malformed evidence')
                continue
            path = (root / item['path']).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                errors.append(f'{label}: missing or unsafe evidence path')
            elif item.get('sha256') != digest(path):
                errors.append(f'{label}: stale evidence {item["path"]}')
        if state in {'met', 'not_applicable'}:
            if not evidence or not row.get('reviewed_by') or not row.get('reviewed_at'):
                errors.append(f'{label}: approval and evidence required for {state}')
            if state == 'not_applicable' and not row.get('applicability_reason'):
                errors.append(f'{label}: explicit applicability rationale required')
        elif release:
            errors.append(f'{label} [{row.get("severity")}]: {state} — {row.get("finding")}')
    if release and data.get('reviewed_source_digest') != source_digest(root):
        errors.append('Source changed or has not been reviewed: refresh candidate evidence')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate register integrity only; does not approve a release')
    parser.add_argument('--fingerprint', action='store_true')
    args = parser.parse_args()
    if args.fingerprint:
        print(source_digest()); return 0
    try:
        data = json.loads((ROOT / REGISTER).read_text(encoding='utf-8'))
        errors = validate(data, release=not args.check)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('BLOCKED: assessment could not be validated ('+type(exc).__name__+')')
        return 1
    if errors:
        print('PRODUCTION BLOCKED' if not args.check else 'INVALID ASSESSMENT')
        for error in errors:
            print('- '+error)
        return 1
    print('REGISTER VALID; production readiness not asserted' if args.check else 'PRODUCTION GUARDRAILS MET for reviewed source')
    return 0


if __name__ == '__main__':
    sys.exit(main())
