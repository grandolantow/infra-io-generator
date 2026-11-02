#!/usr/bin/env python3
"""Run real pinned exports from frozen examples; records evidence, not visual approval."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / 'skills/technical-architecture-diagrams/scripts/figgenie_export.py'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path):
    with zipfile.ZipFile(path) as package:
        slides = [n for n in package.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        result = []
        for name in slides:
            root = ET.fromstring(package.read(name))
            ids = [e.get('id') for e in root.iter(P + 'cNvPr')]
            result.append({'part': name, 'xml_sha256': hashlib.sha256(package.read(name)).hexdigest(),
                           'texts': [e.text for e in root.iter(A + 't')],
                           'shape_count': len(list(root.iter(P + 'sp'))),
                           'connector_count': len(list(root.iter(P + 'cxnSp'))),
                           'freeform_count': len(list(root.iter(A + 'custGeom'))),
                           'group_count': len(list(root.iter(P + 'grpSp'))),
                           'picture_count': len(list(root.iter(P + 'pic'))),
                           'arrow_count': len(list(root.iter(A + 'tailEnd'))),
                           'connection_binding_count': len(list(root.iter(A + 'stCxn'))) + len(list(root.iter(A + 'endCxn'))),
                           'group_names': [e.find(P + 'nvGrpSpPr/' + P + 'cNvPr').get('name') for e in root.iter(P + 'grpSp')],
                           'ids': ids, 'unique_ids': len(ids) == len(set(ids)),
                           'effect_ref_indices': [e.get('idx') for e in root.iter(A + 'effectRef')]})
        return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--upstream', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True, help='new directory; never overwrite an acceptance run')
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'runs': [], 'visual_review': 'not_run', 'office_review': 'not_run'}
    try:
        for case in ('ascend-workflow', 'kv-offload'):
            source = ROOT / 'examples/figgenie' / case
            frozen_hash = sha(source / 'fig.svg')
            manifests = {}
            for mode in ('image', 'pptx', 'both'):
                target = out / case / mode
                cmd = [sys.executable, str(EXPORT), str(source / 'fig.svg'), '--spec', str(source / 'spec.json'),
                       '--upstream', str(args.upstream.resolve()), '--out', str(target),
                       '--output-format', mode, '--display-intent', 'presentation', '--png-scale', '3']
                proc = subprocess.run(cmd, text=True, capture_output=True)
                target.mkdir(parents=True, exist_ok=True)
                (target / 'invocation.txt').write_text(proc.stdout + proc.stderr)
                run = {'case': case, 'mode': mode, 'command': cmd, 'returncode': proc.returncode}
                report['runs'].append(run)
                manifest_path = target / 'manifest.json'
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text())
                    manifests[mode] = manifest
                    run['manifest'] = str(manifest_path.relative_to(out))
                    run['source_svg_sha256'] = manifest['source_svg_sha256']
                    run['outputs'] = manifest['outputs']
                    assert manifest['source_svg_sha256'] == frozen_hash == sha(source / 'fig.svg')
                    assert manifest['design_invocations'] == 0
                    assert all(v['source_svg_sha256'] == frozen_hash for v in manifest['outputs'].values())
                if proc.returncode:
                    run['status'] = 'failed'
                    continue  # Attempt each mode; a shared gate is not three exporter failures.
                run['status'] = 'checking_structure'
                if (target / 'fig.png').exists():
                    header = (target / 'fig.png').read_bytes()[:24]
                    run['png_pixels'] = struct.unpack('>II', header[16:24])
                if (target / 'fig.pptx').exists():
                    run['pptx_inventory'] = inventory(target / 'fig.pptx')
                    assert all(s['shape_count'] > 0 and s['texts'] and s['unique_ids'] and s['picture_count'] == 0 for s in run['pptx_inventory'])
                run['status'] = 'passed_structural_checks_visual_pending'
            if all(m in manifests and manifests[m]['status'] != 'failed' for m in ('image', 'pptx', 'both')):
                for filename in ('fig.final.svg', 'fig.png'):
                    assert manifests['image']['outputs'][filename]['sha256'] == manifests['both']['outputs'][filename]['sha256']
                assert inventory(out / case / 'pptx/fig.pptx') == inventory(out / case / 'both/fig.pptx')
        report['status'] = 'passed_structural_checks_visual_pending' if all(r['returncode'] == 0 for r in report['runs']) else 'failed'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        (out / 'acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'runs': len(report['runs']), 'report': str(out / 'acceptance.json')}))
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
