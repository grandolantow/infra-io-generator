#!/usr/bin/env python3
"""SVG-first compiler: separate semantic truth, authored layout and presentation.

This is a deterministic build tool, not a natural-language designer or a universal
layout optimiser. Legacy report IR remains supported without changing its renderer.
No network, rasterisation, external fonts or browser runtime is required to build.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT.parent / 'technical-diagram-options/scripts/diagram_tool.py'
SCHEMA = 'svg-first/1'
PORTS = {'top': (.5, 0), 'right': (1, .5), 'bottom': (.5, 1), 'left': (0, .5)}
SAFE_ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_.:-]*$')
SAFE_COLOR = re.compile(r'^(?:#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})|[a-zA-Z]+)$')
DEFAULT_STYLE = {'fill': '#FFFFFF', 'stroke': '#AEB8C0', 'stroke_width': 1.5,
                 'font_size': 18, 'font_family': 'sans-serif', 'text_color': '#1D1D1A'}


def backend():
    spec = importlib.util.spec_from_file_location('svg_first_legacy_backend', BACKEND_PATH)
    if spec is None or spec.loader is None or not BACKEND_PATH.is_file():
        raise ValueError('Install both sibling diagram skills; diagram_tool.py is missing.')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                     allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def number(value: Any, label: str, positive: bool = False) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f'{label}: expected a finite number')
    require(not positive or value > 0, f'{label}: must be positive')
    return value


def split_legacy(doc: dict) -> dict:
    """Lossless semantic/geometry migration; does not redesign historical figures."""
    require(doc.get('schema_version') == '1.0', 'Expected report IR schema_version=1.0')
    require(doc.get('language_profile'), 'Declare the shared language profile before migration.')
    out = copy.deepcopy(doc)
    views = out.pop('views')
    out['schema_version'] = SCHEMA
    out['layout'] = {'views': views}
    out.setdefault('theme', {})
    out['migration'] = {'from': 'report-ir/1.0', 'redesigned': False}
    return out


def arrange(view: dict) -> None:
    """Resolve only explicit row/column constraints; never infer relationships."""
    glyphs = {g['id']: g for g in view['glyphs']}
    moved: set[str] = set()
    for item in view.pop('arrangements', []):
        axis = item.get('axis')
        require(axis in ('row', 'column'), 'arrangements.axis must be row or column')
        x = number(item.get('x'), 'arrangement.x')
        y = number(item.get('y'), 'arrangement.y')
        gap = number(item.get('gap', 24), 'arrangement.gap')
        require(gap >= 0, 'arrangement.gap cannot be negative')
        for gid in item.get('members', []):
            require(gid in glyphs and gid not in moved, f'{gid}: missing or multiply arranged')
            g = glyphs[gid]
            require(not g.get('locked'), f'{gid}: locked glyph cannot be rearranged')
            g['x'], g['y'] = x, y
            moved.add(gid)
            if axis == 'row':
                x += number(g['w'], gid + '.w', True) + gap
            else:
                y += number(g['h'], gid + '.h', True) + gap


def port(glyph: dict, name: str) -> list[float]:
    require(name in PORTS, f'Unsupported port: {name!r}')
    dx, dy = PORTS[name]
    return [glyph['x'] + glyph['w'] * dx, glyph['y'] + glyph['h'] * dy]



def resolve_theme(theme: dict) -> dict:
    """Use shared palette tokens only for explicitly named visual roles."""
    result = copy.deepcopy(theme)
    if 'palette' not in theme:
        return result  # Legacy authored styles are not recolored.
    require(theme['palette'] != 'auto', 'Resolve branch defaults before selecting a palette')
    spec = importlib.util.spec_from_file_location('svg_first_palette', ROOT / 'scripts/resolve_palette.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    resolved = module.resolve(palette=theme['palette'], custom=theme.get('custom_tokens'))
    t = resolved['tokens']
    result['base'] = {'fill': t['background']['canvas'], 'stroke': t['line']['default'],
                      'text_color': t['text']['primary'], **theme.get('base', {})}
    roles = {k: {'fill': t[k]['fill'], 'stroke': t[k]['stroke']}
             for k in ('compute', 'state', 'communication', 'rank0', 'rank1')}
    roles['focus'] = {'stroke': t['accent']['primary']}
    roles['panel'] = {'fill': t['background']['panel'], 'stroke': t['line']['default']}
    for k, v in theme.get('roles', {}).items():
        roles[k] = {**roles.get(k, {}), **v}
    result['roles'] = roles
    result['edge'] = {'stroke': t['line']['strong'], **theme.get('edge', {})}
    return result


def compile_scene(scene: dict) -> dict:
    require(scene.get('schema_version') == SCHEMA, f'Expected schema_version={SCHEMA}')
    require(isinstance(scene.get('semantic'), dict), 'semantic is required')
    require(isinstance(scene.get('layout', {}).get('views'), list), 'layout.views is required')
    require(scene.get('language_profile'), 'language_profile must be declared')
    doc = {k: copy.deepcopy(v) for k, v in scene.items()
           if k not in ('layout', 'theme', 'migration')}
    doc['schema_version'] = '1.0'
    doc['views'] = copy.deepcopy(scene['layout']['views'])
    nodes = {n['id']: n for n in doc['semantic']['nodes']}
    theme = scene.get('theme', {})
    require(isinstance(theme, dict), 'theme must be an object')
    theme = resolve_theme(theme)
    for view in doc['views']:
        require(SAFE_ID.fullmatch(view.get('id', '')) is not None, 'Invalid view ID')
        glyphs = view.get('glyphs', [])
        require(len({g['id'] for g in glyphs}) == len(glyphs), 'Duplicate glyph ID')
        view.setdefault('title_text_role', 'diagram_title')
        view.setdefault('scope_text_role', 'prose')
        for g in glyphs:
            ref = g.get('semantic_ref')
            if 'label' not in g and 'label_lines' not in g and ref:
                require(ref in nodes, f'{g["id"]}: unknown semantic node')
                g['label_lines'] = nodes[ref]['label'].split('\n')
                g.setdefault('text_role', 'node_label')
            style = {**DEFAULT_STYLE, **theme.get('base', {}),
                     **theme.get('roles', {}).get(g.get('style_role'), {}),
                     **g.get('style', {})}
            g['style'] = style
        arrange(view)
        by_id = {g['id']: g for g in glyphs}
        for path in view.get('paths', []):
            path['style'] = {**DEFAULT_STYLE, **theme.get('base', {}),
                             **theme.get('edge', {}), **path.get('style', {})}
            if 'source_port' in path or 'target_port' in path:
                require('points' not in path, 'Specify points OR ports/via, not both')
                require('source_port' in path and 'target_port' in path, 'Both ports are required')
                a, b = by_id[path['source_instance']], by_id[path['target_instance']]
                path['points'] = [port(a, path['source_port']), *path.get('via', []),
                                  port(b, path['target_port'])]
                path.pop('source_port')
                path.pop('target_port')
                path.pop('via', None)
    require(fingerprint(doc['semantic']) == fingerprint(scene['semantic']), 'Semantic drift')
    return doc


def validate(doc: dict) -> dict:
    """Add finite bounds, route attachment and output-ID checks to existing QA."""
    for view in doc['views']:
        for item in view['glyphs'] + view.get('paths', []):
            st = item.get('style', {})
            for key in ('fill', 'stroke', 'text_color'):
                require(SAFE_COLOR.fullmatch(str(st.get(key, 'none'))) is not None,
                        f'{item["id"]}: only named or hex colors are supported')
            font = st.get('font_family', 'sans-serif')
            require(isinstance(font, str) and not any(c in font for c in ';<>{}\\'),
                    'Unsupported font-family; CSS injection is not supported')
            number(st.get('font_size', 18), 'font_size', True)
            number(st.get('stroke_width', 1.5), 'stroke_width')
            require(st.get('stroke_width', 1.5) >= 0, 'stroke_width cannot be negative')
            weight = st.get('font_weight', 400)
            require(isinstance(weight, int) and 100 <= weight <= 900, 'Invalid font_weight')
        w = number(view['canvas']['width'], 'canvas.width', True)
        h = number(view['canvas']['height'], 'canvas.height', True)
        # Practical guardrail against unbounded sampled-intersection work.
        require(max(w, h) <= 100000, 'Canvas exceeds supported coordinate range')
        ids = {g['id'] for g in view['glyphs']} | {p['id'] for p in view.get('paths', [])}
        require(not {'0', '1'} & ids, 'IDs 0/1 are reserved by the draw.io adapter')
        glyphs = {g['id']: g for g in view['glyphs']}
        for g in view['glyphs']:
            x, y = number(g['x'], 'x'), number(g['y'], 'y')
            gw, gh = number(g['w'], 'width', True), number(g['h'], 'height', True)
            require(0 <= x <= w - gw and 0 <= y <= h - gh, f'{g["id"]}: outside canvas')
            s = g.get('style', {})
            number(s.get('font_size', 18), 'font_size', True)
            for key in ('fill', 'stroke', 'text_color'):
                require(SAFE_COLOR.fullmatch(str(s.get(key, 'none'))) is not None,
                        f'{g["id"]}: unsupported color {key}; use named or hex colors')
            require(g.get('text_anchor', 'middle') in ('start', 'middle', 'end'), 'Invalid text_anchor')
        for path in view.get('paths', []):
            require('arrow-' + path['id'] not in ids, 'Generated marker ID collision')
            require(len(path.get('points', [])) >= 2, 'Route requires at least two points')
            for p in path['points']:
                require(isinstance(p, (list, tuple)) and len(p) == 2, 'Invalid route point')
                require(0 <= number(p[0], 'route.x') <= w and 0 <= number(p[1], 'route.y') <= h,
                        'Route point outside canvas')
            # Endpoints must attach to the intended object, not float in whitespace.
            for name, point in [('source_instance', path['points'][0]),
                                ('target_instance', path['points'][-1])]:
                require(path.get(name) in glyphs, f'{path["id"]}: missing endpoint')
                g = glyphs[path[name]]
                x, y, gw, gh = [g[k] for k in ('x', 'y', 'w', 'h')]
                px, py = point
                tol = 1e-6
                in_box = x - tol <= px <= x + gw + tol and y - tol <= py <= y + gh + tol
                require(in_box, f'{path["id"]}: endpoint detached from {g["id"]}')
                if g.get('shape', 'rect') in ('rect', 'rounded_rect'):
                    on_boundary = min(abs(px-x), abs(px-x-gw), abs(py-y), abs(py-y-gh)) <= tol
                    require(on_boundary, f'{path["id"]}: endpoint is not on object boundary')
    result = backend().check(doc)
    require(result['valid'], '\n'.join(result['errors']))
    return result


def svg_tree(view: dict, doc: dict) -> ET.Element:
    root = backend().svg_view(view, doc)
    elements = {e.get('id'): e for e in root.iter() if e.get('id')}
    nodes = {n['id']: n for n in doc['semantic']['nodes']}
    for g in view['glyphs']:
        group = elements[g['id']]
        group.set('data-instance-id', g['id'])
        group.set('data-shape', g.get('shape', 'rect'))
        if g.get('semantic_ref'):
            group.set('tabindex', '0')
            group.set('role', 'button')
            group.set('aria-label', nodes[g['semantic_ref']]['label'])
        for text in group.findall('text'):
            text.set('font-weight', str(g.get('style', {}).get('font_weight', 400)))
    # Every inline SVG gets its own ID namespace; semantic IDs remain unchanged.
    mapping = {e.get('id'): f'v{len(view["id"])}-{view["id"]}--{e.get("id")}' for e in root.iter() if e.get('id')}
    require(len(mapping) == len([e for e in root.iter() if e.get('id')]), 'Duplicate rendered ID')
    for e in root.iter():
        if e.get('id'):
            e.set('id', mapping[e.get('id')])
        for key, value in list(e.attrib.items()):
            e.set(key, re.sub(r'url\(#([^)]*)\)', lambda m: 'url(#' + mapping[m[1]] + ')', value))
    return root


def drawio_tree(doc: dict) -> ET.Element:
    root = backend().drawio(doc)
    # Font weight and text alignment were previously silently ignored by this adapter.
    for page, view in zip(root.findall('diagram'), doc['views']):
        cells = {e.get('id'): e for e in page.iter('mxCell')}
        for g in view['glyphs']:
            cell = cells[g['id']]
            weight = g.get('style', {}).get('font_weight', 400)
            anchor = g.get('text_anchor', 'middle')
            st = cell.get('style', '') + f'fontStyle={1 if int(weight) >= 600 else 0};'
            st += 'align=' + {'start': 'left', 'middle': 'center', 'end': 'right'}[anchor] + ';'
            if anchor == 'start':
                st += 'spacingLeft=' + str(g.get('text_x', g['x']) - g['x']) + ';'
            elif anchor == 'end':
                st += 'spacingRight=' + str(g['x'] + g['w'] - g.get('text_x', g['x'] + g['w'])) + ';'
            cell.set('style', st)
    return root


def html_viewer(doc: dict, svgs: dict[str, str]) -> str:
    template = (ROOT / 'assets/svg-first-viewer.html').read_text(encoding='utf-8')
    data = {'diagram_id': doc['diagram_id'], 'semantic': doc['semantic'],
            'views': [{'id': v['id'], 'title': v.get('title', v['id']), 'scope': v['scope']}
                      for v in doc['views']]}
    # JSON in a script element must not be able to terminate the element.
    payload = encoded(data).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    sections = []
    for v in doc['views']:
        sections.append('<section class="view" data-view="' + html.escape(v['id'], quote=True)
                        + '"><div class="viewport">' + svgs[v['id']] + '</div></section>')
    values = {'TITLE': html.escape(doc['diagram_id']), 'VIEWS': '\n'.join(sections), 'DATA': payload}
    return re.sub(r'\{\{(TITLE|VIEWS|DATA)\}\}', lambda m: values[m[1]], template)


def build(scene: dict, output: Path, *, with_drawio: bool = True,
          overwrite_edits: bool = False) -> dict:
    doc = compile_scene(scene)
    result = validate(doc)
    output = Path(output)
    manifest_path = output / 'build-manifest.json'
    svgs = {v['id']: ET.tostring(svg_tree(v, doc), encoding='unicode') for v in doc['views']}
    files = {'scene.source.json': encoded(scene), 'semantic.json': encoded(scene['semantic']),
             'layout.resolved.json': encoded({'views': doc['views']}),
             'diagram.source.json': encoded(doc), 'preview.html': html_viewer(doc, svgs),
             'structural-qa.json': encoded(result)}
    files.update({vid + '.svg': svg for vid, svg in svgs.items()})
    if with_drawio:
        files['diagram.drawio'] = ET.tostring(drawio_tree(doc), encoding='unicode')
    # Catch edits in published SVG, HTML or draw.io before re-generating them.
    old = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    for name in old.get('artifacts', {}):
        require(Path(name).name == name and name not in ('.', '..'), 'Unsafe artifact path in manifest')
    if not overwrite_edits:
        for name in set(files) | set(old.get('artifacts', {})):
            p = output / name
            if p.exists():
                known = old.get('artifacts', {}).get(name)
                require(known is not None and hashlib.sha256(p.read_bytes()).hexdigest() == known,
                        f'{name}: modified/untracked output; reconcile edits before rebuilding')
    manifest = {'schema_version': 1, 'renderer': 'svg-first',
                'semantic_sha256': fingerprint(scene['semantic']),
                'scene_sha256': fingerprint(scene),
                'artifacts': {n: hashlib.sha256(s.encode('utf-8')).hexdigest() for n, s in files.items()},
                'validation': {'structural': 'pass', 'language_contract': result['language_qa']['contract_status'],
                               'source_fact_review': 'not_run', 'visual': 'not_run',
                               'browser': 'not_run', 'drawio_editor': 'not_run', 'GUI_drag': 'not_run'},
                'export_limits': ['draw.io is a one-way editable export, not lossless round-trip.',
                                  'Font metrics/label positions may differ; inspect the actual editor.',
                                  'HTML selection follows graph relations, not measured execution order.',
                                  'No PNG/PDF/PPT rendering or independent-agent execution is claimed.']}
    output.mkdir(parents=True, exist_ok=True)
    for name in set(old.get('artifacts', {})) - set(files):
        require(Path(name).name == name, 'Unsafe path in previous manifest')
        (output / name).unlink(missing_ok=True)
    for name, content in files.items():
        tmp = output / (name + '.tmp')
        tmp.write_text(content, encoding='utf-8')
        tmp.replace(output / name)
    manifest_path.write_text(encoded(manifest), encoding='utf-8')
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['split', 'check', 'build'])
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--out-dir', type=Path, default=Path('build/svg-first'))
    parser.add_argument('--no-drawio', action='store_true')
    parser.add_argument('--overwrite-edits', action='store_true')
    args = parser.parse_args()
    try:
        scene = json.loads(args.input.read_text(encoding='utf-8'))
        if args.command == 'split':
            require(args.out is not None, 'split requires --out')
            require(not args.out.exists(), 'split refuses to overwrite an existing source')
            result = split_legacy(scene)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(encoded(result), encoding='utf-8')
            print(encoded({'source': str(args.out), 'semantic_sha256': fingerprint(result['semantic'])}))
        elif args.command == 'check':
            print(encoded(validate(compile_scene(scene))))
        else:
            print(encoded(build(scene, args.out_dir, with_drawio=not args.no_drawio,
                                overwrite_edits=args.overwrite_edits)))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'svg_pipeline: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
