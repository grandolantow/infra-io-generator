#!/usr/bin/env python3
"""Color-only adapter, not a semantic compiler. Requires explicit mapping.

SVG map: {"#oldhex": "compute.fill"}; changes matching SVG color attributes
and inline style declarations only (not CSS stylesheets, text, geometry or IDs).
Drawio map: {"cell-id": {"fillColor":"compute.fill", "fontColor":"text.primary"}}.
Only existing color style properties in native uncompressed XML are replaced.
Unsupported forms fail rather than infer roles or add properties. Writes a new file.
"""
import argparse
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from resolve_palette import resolve, flatten, HEX

SVG_PROPERTIES = {'fill','stroke','color','stop-color','flood-color','lighting-color'}
DRAWIO_PROPERTIES = {'fillColor','strokeColor','fontColor','gradientColor','labelBackgroundColor','labelBorderColor','swimlaneFillColor'}
# Quoted XML attribute values may legally contain > and the opposite quote.
# Consume whole quoted strings before recognizing the closing tag delimiter.
TAG = re.compile(r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>", re.S)
ATTR = re.compile(r'(?<=\s)(?P<key>[\w:.-]+)(?P<eq>\s*=\s*)(?P<quote>[\"\x27])(?P<value>.*?)(?P=quote)', re.S)


def checked_xml(source):
    if '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper():
        raise ValueError('DTD/entity XML unsupported')
    return ET.fromstring(source)


def replace_attr(match, value):
    return match['key'] + match['eq'] + match['quote'] + value + match['quote']


def token_value(tokens, role):
    if not isinstance(role, str) or role not in tokens:
        raise ValueError(f'Unknown semantic token: {role!r}')
    return tokens[role]


def apply_svg(source, mapping, tokens):
    root = checked_xml(source)
    if root.tag.split('}')[-1] != 'svg':
        raise ValueError('Expected SVG root')
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('Nonempty explicit SVG source-color map required')
    replacements = {}
    for color, role in mapping.items():
        if not HEX.fullmatch(color):
            raise ValueError('SVG map source colors must be six-digit hex')
        if color.upper() in replacements:
            raise ValueError('Duplicate case-insensitive source color')
        replacements[color.upper()] = token_value(tokens, role)
    seen = set()
    def recolor(value):
        stripped = value.strip()
        if stripped.upper() in replacements:
            seen.add(stripped.upper())
            return value.replace(stripped, replacements[stripped.upper()], 1)
        return value
    def attr(m):
        if m['key'] in SVG_PROPERTIES:
            return replace_attr(m, recolor(m['value']))
        if m['key'] == 'style':
            # Parse only individual declaration values, never text or arbitrary URLs.
            style = re.sub(r'(^|;)(\s*)([\w-]+)(\s*:\s*)([^;]*)',
                lambda d: d[1]+d[2]+d[3]+d[4]+(recolor(d[5]) if d[3] in SVG_PROPERTIES else d[5]), m['value'])
            return replace_attr(m, style)
        return m[0]
    result = TAG.sub(lambda t: t[0] if t[0].startswith(('<!--','<!','<?','</')) else ATTR.sub(attr,t[0]), source)
    if set(replacements) != seen:
        raise ValueError(f'Unmatched SVG source colors: {sorted(set(replacements)-seen)}')
    checked_xml(result)
    return result


def apply_drawio(source, mapping, tokens):
    root = checked_xml(source)
    if root.tag not in ('mxfile','mxGraphModel'):
        raise ValueError('Expected native drawio XML')
    diagrams = list(root.iter('diagram'))
    if any(not list(d) or d.find('mxGraphModel') is None for d in diagrams):
        raise ValueError('Compressed drawio unsupported; save uncompressed XML first')
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('Nonempty explicit cell-property map required')
    for cell, props in mapping.items():
        if not isinstance(cell,str) or not isinstance(props,dict) or not props or set(props)-DRAWIO_PROPERTIES:
            raise ValueError('Invalid cell ID/property map')
        for role in props.values():
            token_value(tokens,role)
    ids=[c.get('id') for c in root.iter('mxCell')]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate mxCell IDs')
    seen = set()
    def tag(t):
        value=t[0]
        if not re.match(r'<mxCell(?:\s|/|>)',value):
            return value
        attrs={m['key']:m for m in ATTR.finditer(value)}
        cell=html.unescape(attrs['id']['value']) if 'id' in attrs else None
        if cell not in mapping:
            return value
        if 'style' not in attrs:
            raise ValueError(f'Cell {cell} has no style')
        props=mapping[cell]
        changed=set()
        def declaration(d):
            key=d[2]
            if key not in props:
                return d[0]
            if key in changed:
                raise ValueError(f'Duplicate style property {cell}.{key}')
            changed.add(key)
            return d[1]+key+'='+token_value(tokens,props[key])
        style=re.sub(r'(^|;)([\w]+)=([^;]*)', declaration, attrs['style']['value'])
        if changed != set(props):
            raise ValueError(f'Mapped color property missing in cell {cell}')
        seen.add(cell)
        return ATTR.sub(lambda m:replace_attr(m,style) if m['key']=='style' else m[0],value)
    result=TAG.sub(tag,source)
    if seen != set(mapping):
        raise ValueError(f'Unknown cell IDs: {sorted(set(mapping)-seen)}')
    checked_xml(result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--map',type=Path,required=True)
    p.add_argument('--target',choices=['ppt','paper'])
    p.add_argument('--palette',default='auto')
    p.add_argument('--custom',type=Path)
    a=p.parse_args()
    try:
        if a.input.resolve()==a.output.resolve():
            raise ValueError('Output must differ from input; preserve the original')
        result=resolve(a.target,a.palette,json.loads(a.custom.read_text()) if a.custom else None)
        # newline="" preserves original line endings outside replacements.
        with a.input.open(newline='') as f:
            source=f.read()
        adapter={'.svg':apply_svg,'.drawio':apply_drawio}.get(a.input.suffix.lower())
        if adapter is None:
            raise ValueError('Only .svg and uncompressed .drawio supported')
        rendered=adapter(source,json.loads(a.map.read_text()),flatten(result['tokens']))
        with a.output.open('w',newline='') as f:
            f.write(rendered)
    except (ValueError,OSError,TypeError,KeyError,ET.ParseError) as exc:
        p.exit(2,f'palette error: {exc}\n')

if __name__=='__main__':
    main()
