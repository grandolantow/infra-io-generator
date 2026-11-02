#!/usr/bin/env python3
"""Thin, stdlib-only orchestration of a pinned FigGenie SVG. Never designs a figure."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

CONFIG = Path(__file__).resolve().parents[1] / 'config/figgenie.json'
SVG_NS = 'http://www.w3.org/2000/svg'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_format(value):
    aliases = {'png': 'image', 'svg': 'image', 'ppt': 'pptx', '图片': 'image', '可编辑 PPT': 'pptx', '两种都要': 'both'}
    value = aliases.get(value, value)
    if value not in ('image', 'pptx', 'both'):
        raise ValueError('output_format must be image, pptx, or both')
    return value


def inspect_svg(path):
    """Reject lossy features before calling the native exporter; not a parallel linter."""
    root = ET.parse(path).getroot()
    if root.tag != f'{{{SVG_NS}}}svg' or not root.get('viewBox'):
        raise ValueError('canonical SVG must have an SVG root and explicit viewBox')
    values = [float(v) for v in root.get('viewBox').replace(',', ' ').split()]
    if len(values) != 4 or values[:2] != [0.0, 0.0] or min(values[2:]) <= 0:
        raise ValueError('canonical viewBox must be 0 0 W H with positive dimensions')
    unsupported, ids, formulas = [], [], []
    for el in root.iter():
        tag = el.tag.split('}')[-1]
        if tag in ('linearGradient', 'radialGradient', 'filter', 'foreignObject', 'use', 'switch', 'tspan', 'clipPath', 'mask'):
            unsupported.append(tag)
        if tag == 'use':
            href = el.get('href', el.get('{http://www.w3.org/1999/xlink}href', ''))
            if not href.startswith('#'):
                unsupported.append('external <use>')
        if tag == 'style' and (el.text or '').strip():
            unsupported.append('CSS style sheet (use presentation attributes or inline style)')
        if el.get('data-symbol') == 'tex':
            formulas.append(el)
            if not all(el.get(k) is not None for k in ('data-w', 'data-asc', 'data-desc', 'data-baseline')):
                raise ValueError('formula has no native tex_fill metrics; complete FigGenie formula rendering first')
        if any(el.get(k) is not None for k in ('clip-path', 'mask', 'display', 'visibility', 'filter')):
            unsupported.append('clipping/masking/visibility attributes')
        inline = el.get('style', '').lower()
        if re.search(r'(?:^|;)\s*(?:clip-path|mask|display|visibility|filter)\s*:', inline):
            unsupported.append('clipping/masking/visibility inline style')
        if el.get('id'):
            ids.append(el.get('id'))
    if unsupported:
        raise ValueError('unsupported SVG elements (no raster fallback): ' + ', '.join(sorted(set(unsupported))))
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate SVG IDs')
    top_groups = [el.get('id') for el in root if el.tag == f'{{{SVG_NS}}}g' and el.get('id')]
    nested_groups = [el.get('id') for top in root if top.tag == f'{{{SVG_NS}}}g' and top.get('data-symbol') != 'tex' for el in top.iter() if el is not top and el.tag == f'{{{SVG_NS}}}g']
    if nested_groups:
        raise ValueError('nested SVG groups are flattened by upstream PPT export; use top-level semantic groups and visual containers')
    return {'viewBox': root.get('viewBox'), 'object_ids': ids, 'semantic_group_ids': top_groups, 'formula_count': len(formulas)}


def run_export(args):
    config = json.loads(CONFIG.read_text())
    mode = normalize_format(args.output_format)
    upstream = Path(args.upstream or os.environ.get('FIGGENIE_CHECKOUT', '')).resolve()
    if not args.upstream and not os.environ.get('FIGGENIE_CHECKOUT'):
        raise ValueError('provide --upstream CHECKOUT or FIGGENIE_CHECKOUT; no automatic install')
    revision = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    expected = config['upstream_revision']
    if revision != expected:
        raise ValueError(f'upstream revision mismatch: expected {expected}, got {revision}')
    if subprocess.run(['git', '-C', str(upstream), 'diff', '--quiet', 'HEAD']).returncode:
        raise ValueError('upstream checkout has tracked modifications; use a clean pinned checkout')
    scripts = upstream / config['skill_path'] / 'scripts'
    svg, spec, out = args.svg.resolve(), args.spec.resolve(), args.out.resolve()
    if not svg.is_file() or not spec.is_file():
        raise ValueError('canonical SVG and native spec.json must exist')
    if out == svg.parent or out in svg.parents or out == spec.parent:
        raise ValueError('use a separate output directory; source files are never overwritten')
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        raise ValueError('output directory is not empty; it may contain hand edits. Use a new directory or explicit --overwrite permission')
    if out.exists() and any(p.is_symlink() for p in out.rglob('*')):
        raise ValueError('output contains symlinks; refuse to overwrite linked user/source files')
    out.mkdir(parents=True, exist_ok=True)
    # Logs are internal checks, not additional default deliverables.
    checks = out / 'checks'
    checks.mkdir(exist_ok=True)
    source_hash = sha(svg)
    spec_hash = sha(spec)
    manifest = {'source_svg_sha256': source_hash, 'source_spec_sha256': spec_hash,
                'upstream_repository': config['upstream_repository'], 'upstream_revision': revision,
                'parameters': {'output_format': mode, 'display_intent': args.display_intent,
                               'png_scale': args.png_scale, 'math': args.math},
                'design_invocations': 0, 'status': 'running', 'commands': [], 'outputs': {},
                'visual_review': 'not_run', 'pptx_render_review': 'not_run', 'warnings': [],
                'limitations': ['Export does not imply visual acceptance or semantic rerouting in PowerPoint.',
                                'Presentation display intent must already be designed into the canonical SVG.',
                                'Top-level semantic group IDs survive in PPT object names; primitive XML IDs are regenerated by the native exporter.']}
    def unchanged():
        if sha(svg) != source_hash or sha(spec) != spec_hash:
            raise RuntimeError('source changed during export; outputs are invalid, regenerate from a fixed source')
    def invoke(name, *arguments):
        unchanged()
        cmd = [sys.executable, str(scripts / name), *map(str, arguments)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        log = checks / (name.removesuffix('.py') + '.txt')
        log.write_text(p.stdout + p.stderr, encoding='utf-8')
        manifest['warnings'].extend(line.strip() for line in (p.stdout + p.stderr).splitlines() if '[warn]' in line or 'WARNING' in line)
        manifest['commands'].append({'command': cmd, 'returncode': p.returncode, 'log': str(log.relative_to(out))})
        unchanged()
        if p.returncode:
            raise RuntimeError(f'{name} failed ({p.returncode}); see {log}')
    try:
        manifest['scene'] = inspect_svg(svg)
        invoke('check.py', svg, '--spec', spec, '--scale', args.png_scale, '--out-dir', checks, '--no-preview')
        lint_file = checks / f'{svg.stem}.lint.json'
        if lint_file.exists():
            lint = json.loads(lint_file.read_text())
            manifest['lint'] = {key: lint.get(key) for key in ('errors', 'warnings', 'findings')}
        if mode in ('image', 'both'):
            invoke('embed_fonts.py', svg, '-o', out / 'fig.final.svg')
            (out / 'fig.png').write_bytes((checks / f'{svg.stem}.png').read_bytes())
            for name in ('fig.final.svg', 'fig.png'):
                manifest['outputs'][name] = {'sha256': sha(out / name), 'source_svg_sha256': source_hash}
        if mode in ('pptx', 'both'):
            effective_math = args.math
            if manifest['scene']['formula_count'] and args.math == 'omml' and not (scripts / 'mathjax/node_modules/mathjax-full').is_dir():
                effective_math = 'text'
                manifest['limitations'].append('MathJax absent: formula export explicitly downgraded to text; no automatic npm install.')
            manifest['parameters']['effective_math'] = effective_math
            opts = ['--force'] if args.overwrite else []
            invoke('svg2pptx.py', svg, '--spec', spec, '-o', out / 'fig.pptx', '--math', effective_math, *opts)
            invoke('pptx_check.py', out / 'fig.pptx', '--svg', svg)
            manifest['outputs']['fig.pptx'] = {'sha256': sha(out / 'fig.pptx'), 'source_svg_sha256': source_hash}
            manifest['limitations'].append('Read checks/svg2pptx.txt for font mappings and native-equation fallback warnings.')
        unchanged()
        manifest['status'] = 'checks_passed_visual_review_pending'
    except Exception as exc:
        manifest['status'] = 'failed'
        manifest['error'] = str(exc)
        raise
    finally:
        (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('svg', type=Path)
    ap.add_argument('--spec', required=True, type=Path)
    ap.add_argument('--upstream', help='clean checkout at config/figgenie.json revision')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--output-format', '--output_format', default='image')
    ap.add_argument('--display-intent', choices=('paper', 'presentation'), default='paper')
    ap.add_argument('--png-scale', type=float, default=3.0)
    ap.add_argument('--math', choices=('omml', 'text'), default='omml')
    ap.add_argument('--overwrite', action='store_true', help='explicit permission to overwrite existing generated files, including manual edits')
    args = ap.parse_args()
    if args.png_scale <= 0:
        ap.error('--png-scale must be positive')
    try:
        result = run_export(args)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, ET.ParseError) as exc:
        ap.exit(1, f'{exc}\n')
    print(json.dumps({'status': result['status'], 'source_svg_sha256': result['source_svg_sha256'], 'outputs': list(result['outputs'])}))


if __name__ == '__main__':
    main()
