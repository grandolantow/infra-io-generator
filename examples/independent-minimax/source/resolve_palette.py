#!/usr/bin/env python3
"""Resolve semantic colors; does not infer semantics or alter layout.

Examples: resolve_palette.py --target ppt --format css
          resolve_palette.py --palette custom --custom overrides.json
Overrides are a sparse nested token object, e.g. {"accent":{"primary":"#C00000"}}.
Precedence: target default < explicit palette < custom overrides.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import sys

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'references' / 'palettes.json'
ROLES = {'text': ('primary', 'secondary'), 'background': ('canvas', 'panel'),
         'line': ('default', 'strong'), 'accent': ('primary',),
         **{k: ('fill', 'stroke') for k in ('compute', 'state', 'communication', 'rank0', 'rank1')}}
HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')


def validate_tokens(tokens, partial=False):
    if not isinstance(tokens, dict) or not tokens:
        raise ValueError('Token object must be nonempty')
    if set(tokens) - set(ROLES) or (not partial and set(tokens) != set(ROLES)):
        raise ValueError('Unknown or missing token groups')
    for group, values in tokens.items():
        if not isinstance(values, dict) or not values:
            raise ValueError('Token groups must be nonempty objects')
        if set(values) - set(ROLES[group]) or (not partial and set(values) != set(ROLES[group])):
            raise ValueError(f'Unknown or missing roles in {group}')
        for role, value in values.items():
            if not isinstance(value, str) or not HEX.fullmatch(value):
                raise ValueError(f'Invalid six-digit hex at {group}.{role}: {value!r}')


def luminance(color):
    values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    values = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v*w for v, w in zip(values, (.2126, .7152, .0722)))


def contrast(a, b):
    x, y = sorted((luminance(a), luminance(b)))
    return (y + .05) / (x + .05)


def validate_contrast(tokens):
    backgrounds = ['#FFFFFF', *tokens['background'].values(),
                   *(tokens[k]['fill'] for k in ('compute','state','communication','rank0','rank1'))]
    for bg in backgrounds:
        if contrast(tokens['text']['primary'], bg) < 4.5:
            raise ValueError(f'Primary text contrast must be >= 4.5 on {bg}')


def resolve(target=None, palette='auto', custom=None, config_path=DEFAULT_CONFIG):
    config = json.loads(Path(config_path).read_text())
    if not isinstance(config, dict) or config.get('schema_version') != 1:
        raise ValueError('Unsupported palette schema_version')
    if (config.get('default_target') not in ('ppt', 'paper')
            or not isinstance(config.get('target_defaults'), dict)
            or set(config['target_defaults']) != {'ppt','paper'}):
        raise ValueError('Invalid target configuration')
    presets = config.get('palettes', {})
    if not isinstance(presets, dict) or set(presets) != {'huawei-plain', 'paper-vivid', 'paper-clear', 'blue-neutral'}:
        raise ValueError('Unknown or missing palette presets')
    for tokens in presets.values():
        validate_tokens(tokens)
        validate_contrast(tokens)
    if any(name not in presets for name in config['target_defaults'].values()):
        raise ValueError('Invalid target default palette')
    target = config['default_target'] if target is None else target
    if target not in config['target_defaults']:
        raise ValueError(f'Unknown target: {target}')
    if palette not in (*presets, 'auto', 'custom'):
        raise ValueError(f'Unknown palette: {palette}')
    if palette == 'custom' and custom is None:
        raise ValueError('palette=custom requires nonempty custom overrides')
    selected = config['target_defaults'][target] if palette in ('auto','custom') else palette
    tokens = copy.deepcopy(presets[selected])
    if custom is not None:
        validate_tokens(custom, partial=True)
        for group, values in custom.items():
            tokens[group].update(values)
    validate_contrast(tokens)
    tokens = {g: {k: v.upper() for k, v in values.items()} for g, values in tokens.items()}
    return {'schema_version':1, 'target':target, 'palette':selected,
            'customized':custom is not None, 'tokens':tokens}


def flatten(tokens):
    return {f'{g}.{k}': v for g, values in tokens.items() for k, v in values.items()}


def output(result, format='json'):
    t = result['tokens']
    if format == 'json':
        return json.dumps(result, indent=2)
    if format == 'css':
        return ':root {\n' + '\n'.join(f'  --diagram-{k.replace(".", "-")}: {v};' for k,v in flatten(t).items()) + '\n}'
    if format == 'drawio':
        styles = {k: f'fillColor={t[k]["fill"]};strokeColor={t[k]["stroke"]};fontColor={t["text"]["primary"]};'
                  for k in ('compute','state','communication','rank0','rank1')}
        styles.update({
            'panel': f'fillColor={t["background"]["panel"]};strokeColor={t["line"]["default"]};fontColor={t["text"]["primary"]};',
            'edge': f'strokeColor={t["line"]["strong"]};fontColor={t["text"]["primary"]};',
            'accent': f'strokeColor={t["accent"]["primary"]};fontColor={t["text"]["primary"]};',
            'canvas': f'fillColor={t["background"]["canvas"]};',
            'secondary-text': f'fontColor={t["text"]["secondary"]};',
        })
        return json.dumps(styles, indent=2)
    raise ValueError(f'Unknown output format: {format}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target', choices=['ppt','paper'])
    p.add_argument('--palette', default='auto')
    p.add_argument('--custom', type=Path, help='Sparse nested token JSON overrides')
    p.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    p.add_argument('--format', choices=['json','css','drawio'], default='json')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    try:
        result = resolve(a.target, a.palette, json.loads(a.custom.read_text()) if a.custom else None, a.config)
        rendered = output(result, a.format) + '\n'
        if a.output:
            a.output.write_text(rendered)
        else:
            print(rendered, end='')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(2, f'palette error: {exc}\n')

if __name__ == '__main__':
    main()
