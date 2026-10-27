#!/usr/bin/env python3
"""Repository smoke checks; optional actual Graph canvas regressions."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/technical-architecture-diagrams'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--runtime', action='store_true')
    ap.add_argument('--out', type=Path, default=ROOT / 'build/checks.json')
    a = ap.parse_args()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'DIAGRAM_RUNTIME_TESTS': '1' if a.runtime else '0'}
    if a.runtime and not env.get('CHROME_BINARY'):
        sys.path.insert(0, str(ROOT / 'tools'))
        from render_example import chrome_path
        env['CHROME_BINARY'] = chrome_path(None)
    checks = []
    def run(name, args):
        p = subprocess.run([str(x) for x in args], cwd=ROOT, env=env, text=True, capture_output=True)
        checks.append({'name': name, 'passed': p.returncode == 0, 'output': (p.stdout + p.stderr).strip()})
    run('palette-tests', [sys.executable, SKILL / 'scripts/test_palettes.py'])
    run('repository-tests', [sys.executable, '-m', 'unittest', 'discover', '-s', ROOT / 'tests', '-v'])
    run('legacy-fact-contract', [sys.executable, SKILL / 'scripts/validate_spec.py', SKILL / 'references/example-attention.json'])
    with tempfile.TemporaryDirectory() as d:
        run('golden-build', [sys.executable, SKILL / 'assets/golden-refined/build.py', '--out', d])
        run('golden-verify', [sys.executable, SKILL / 'assets/golden-refined/verify.py', d])
    result = {'version': '0.9.7', 'scope': 'repository checks; not scientific or aesthetic certification',
              'runtime_tests_enabled': a.runtime, 'passed': all(c['passed'] for c in checks), 'checks': checks}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, ensure_ascii=False))
    for c in checks:
        print(c['name'], 'PASS' if c['passed'] else 'FAIL')
        if not c['passed']:
            print(c['output'])
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
