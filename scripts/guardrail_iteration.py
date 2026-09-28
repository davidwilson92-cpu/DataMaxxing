"""Run an assessment/verification iteration without granting production approval.

Usage: python scripts/guardrail_iteration.py --output /safe/evidence/directory
Creates a fresh per-run directory; never deletes an earlier run. Tests inherit
the repository's isolated synthetic environment. Provider calls are mocked.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

from release_gate import ROOT, REGISTER, source_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve() / ('iteration-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True, exist_ok=False)
    steps = [
        ('assessment', [sys.executable, 'scripts/release_gate.py', '--check']),
        ('tests', [sys.executable, '-m', 'pytest', '-q', '--basetemp='+str(output/'tmp'), '--junitxml='+str(output/'tests.xml')]),
        ('production', [sys.executable, 'scripts/release_gate.py']),
    ]
    results = {}
    for name, command in steps:
        print('Running '+name, flush=True)
        with (output / (name+'.log')).open('w', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        results[name] = result.returncode
        print(name+': '+('passed' if result.returncode == 0 else 'blocked/failed'), flush=True)
    try:
        data = json.loads((ROOT / REGISTER).read_text(encoding='utf-8'))
        unresolved = sorted((r for r in data['sections'] if r['status'] not in {'met','not_applicable'}), key=lambda r:(r['severity'],r['id']))
        next_actions = [{'section': r['id'], 'severity': r['severity'], 'owner': r['owner'], 'next_action': r['next_action']} for r in unresolved]
    except (OSError, ValueError, KeyError, TypeError):
        next_actions = [{'next_action': 'Repair the assessment before continuing.'}]
    report = {'at': datetime.now(timezone.utc).isoformat(), 'source_digest': source_digest(),
              'checks': results, 'local_iteration_passed': all(code == 0 for code in results.values()),
              'next_actions': next_actions,
              'limits': 'This local iteration does not run PostgreSQL, hosting, live providers, load tests, or independent reviews. Required CI and operational evidence still apply.'}
    (output/'iteration.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('Evidence: '+str(output))
    return 0 if report['local_iteration_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
