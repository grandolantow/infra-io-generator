#!/usr/bin/env python3
"""Thin, stdlib-only orchestration of a pinned FigGenie SVG. Never designs a figure."""
import argparse
import hashlib
import json
import os
import posixpath
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
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
        if any(el.get(k) is not None for k in ('clip-path', 'mask', 'display', 'visibility', 'filter', 'text-shadow', 'box-shadow')):
            unsupported.append('clipping/masking/visibility attributes')
        inline = el.get('style', '').lower()
        if '\\' in inline or '/*' in inline:
            unsupported.append('escaped/commented inline CSS (cannot prove effect-free)')
        if re.search(r'(?:^|;)\s*(?:clip-path|mask|display|visibility|filter|text-shadow|box-shadow)\s*:', inline):
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


def normalize_generated_pptx(svg, generated, output):
    """Remove only accidental shadow-only theme references from a fresh export.

    This is not an in-place PPT editor. The caller supplies a newly generated
    staging file; the destination must not exist. Unsupported SVG effects fail
    closed, and explicit object effects are preserved. No drawing library needed.
    """
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('compatibility output must be a new file')
    inspect_svg(svg)  # Never infer absence of effects from an unsupported SVG.
    a = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    p = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
    rel_ns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
    changes, patched = [], {}
    with zipfile.ZipFile(generated) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError('duplicate PPTX package parts')

        def related(part, kind):
            rel_path = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
            try:
                rels = ET.fromstring(package.read(rel_path))
            except KeyError as exc:
                raise ValueError(f'missing relationships for {part}') from exc
            if any(r.get('Type', '').endswith('/themeOverride') for r in rels):
                raise ValueError('themeOverride is not supported by the shadow compatibility pass')
            matches = [r for r in rels.findall(rel_ns + 'Relationship') if r.get('Type', '').endswith('/' + kind)]
            if len(matches) != 1 or matches[0].get('TargetMode') == 'External':
                raise ValueError(f'expected one internal {kind} relationship for {part}')
            target = matches[0].get('Target', '')
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(part), target)) if not target.startswith('/') else target[1:]
            if resolved not in names:
                raise ValueError(f'missing related PPTX part: {resolved}')
            return resolved

        slides = sorted(n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n))
        if not slides:
            raise ValueError('generated PPTX has no slide XML')
        for part in slides:
            raw = package.read(part)
            root = ET.fromstring(raw)
            refs = list(root.iter(a + 'effectRef'))
            if not refs:
                continue
            layout = related(part, 'slideLayout')
            master = related(layout, 'slideMaster')
            theme = related(master, 'theme')
            styles = ET.fromstring(package.read(theme)).find('.//' + a + 'effectStyleLst')
            if styles is None:
                raise ValueError(f'missing theme effectStyleLst: {theme}')
            edits = {}
            for shape in root.iter():
                if shape.tag not in (p + 'sp', p + 'cxnSp'):
                    continue
                ref = shape.find(p + 'style/' + a + 'effectRef')
                if ref is None:
                    continue
                try:
                    idx = int(ref.get('idx', ''))
                except ValueError as exc:
                    raise ValueError('invalid effectRef index') from exc
                if idx == 0:
                    continue
                if idx < 0 or idx > len(styles):
                    raise ValueError('effectRef index outside theme effectStyleLst')
                props = shape.find(p + 'spPr')
                if props is not None and any(len(e) for e in props if e.tag in (a + 'effectLst', a + 'effectDag')):
                    continue  # Preserve explicitly authored effects, even in fresh exports.
                style = styles[idx - 1]
                effects = style.find(a + 'effectLst')
                shadows = {a + n for n in ('outerShdw', 'innerShdw', 'prstShdw')}
                if effects is None or not any(e.tag in shadows for e in effects):
                    continue
                if any(e.tag not in shadows for e in effects) or any(e.tag != a + 'effectLst' for e in style):
                    raise ValueError('shadow theme style has additional effects; refusing lossy removal')
                number = refs.index(ref)
                edits[number] = idx
                identity = shape.find('.//' + p + 'cNvPr')
                changes.append({'part': part, 'object_id': identity.get('id') if identity is not None else None,
                                'object_name': identity.get('name') if identity is not None else None,
                                'theme': theme, 'before_idx': idx, 'after_idx': 0})
                ref.set('idx', '0')
            if not edits:
                continue
            # Preserve original XML bytes, namespaces and all unrelated attributes.
            tags = list(re.finditer(rb'<(?:[A-Za-z_][\w.-]*:)?effectRef\b[^>]*>', raw))
            if len(tags) != len(refs):
                raise ValueError('ambiguous effectRef XML; refusing compatibility rewrite')
            modified = raw
            for number in sorted(edits, reverse=True):
                match = tags[number]
                tag, count = re.subn(rb'(\sidx\s*=\s*[\x22\x27])\d+([\x22\x27])', rb'\g<1>0\2', match.group())
                if count != 1:
                    raise ValueError('ambiguous effectRef index attribute')
                modified = modified[:match.start()] + tag + modified[match.end():]
            if ET.tostring(ET.fromstring(modified)) != ET.tostring(root):
                raise ValueError('compatibility invariant failed: unrelated XML changed')
            patched[part] = modified
        # Exclusive creation guards against accidental in-place/user-file edits.
        with output.open('xb') as stream, zipfile.ZipFile(stream, 'w') as result:
            result.comment = package.comment
            for info in package.infolist():
                result.writestr(info, patched.get(info.filename, package.read(info.filename)))
    return {'status': 'applied' if changes else 'not_needed', 'changed_references': len(changes),
            'changes': changes, 'before_sha256': sha(generated), 'after_sha256': sha(output),
            'invariant': 'all_package_parts_unchanged_except_selected_effectRef_indices'}


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
    # FontTools otherwise stamps each embedded subset with the wall-clock time.
    # Its supported reproducible-build environment changes no SVG geometry.
    epoch = subprocess.check_output(['git', '-C', str(upstream), 'show', '-s', '--format=%ct', 'HEAD'], text=True).strip()
    tool_env = {**os.environ, 'SOURCE_DATE_EPOCH': epoch}
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
                'tool_environment': {'SOURCE_DATE_EPOCH': epoch},
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
        p = subprocess.run(cmd, capture_output=True, text=True, env=tool_env)
        log = checks / (name.removesuffix('.py') + '.txt')
        log.write_text(p.stdout + p.stderr, encoding='utf-8')
        manifest['warnings'].extend(line.strip() for line in (p.stdout + p.stderr).splitlines()
                                    if re.search(r'\[warn\s*\]|\bWARN(?:ING)?\b|warning:', line, re.I))
        manifest['commands'].append({'command': cmd, 'returncode': p.returncode, 'log': str(log.relative_to(out))})
        unchanged()
        if p.returncode:
            raise RuntimeError(f'{name} failed ({p.returncode}); see {log}')
    try:
        manifest['scene'] = inspect_svg(svg)
        invoke('spec_validate.py', spec)
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
            # Never repair existing output. Export/check a fresh package before
            # publishing; even explicitly allowed overwrite preserves old PPT
            # bytes if generation, normalization or validation fails.
            with tempfile.TemporaryDirectory(prefix='.pptx-stage-', dir=out) as staging:
                raw = Path(staging) / 'raw.pptx'
                compatible = Path(staging) / 'fig.pptx'
                invoke('svg2pptx.py', svg, '--spec', spec, '-o', raw, '--math', effective_math)
                manifest['pptx_compatibility'] = normalize_generated_pptx(svg, raw, compatible)
                invoke('pptx_check.py', compatible, '--svg', svg)
                unchanged()
                os.replace(compatible, out / 'fig.pptx')
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
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, ET.ParseError, zipfile.BadZipFile) as exc:
        ap.exit(1, f'{exc}\n')
    print(json.dumps({'status': result['status'], 'source_svg_sha256': result['source_svg_sha256'], 'outputs': list(result['outputs'])}))


if __name__ == '__main__':
    main()
