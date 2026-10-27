#!/usr/bin/env python3
"""Role/character checks for diagram text; never a semantic language certification.

CLI hashes the exact input bytes. Report API accepts parsed IR; model API accepts
uncompressed draw.io XML bytes/text or an Element. No text is translated.
"""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'references/language-profile.json'
PROFILE_CONFIG = json.loads(CONFIG_PATH.read_text())
PROFILE = PROFILE_CONFIG['id']
TEXT_ROLES = frozenset(PROFILE_CONFIG['roles'])
CONTEXT_ROLES = frozenset(k for k, v in PROFILE_CONFIG['roles'].items() if v['language'] == 'zh')
ENGLISH_ROLES = frozenset(k for k, v in PROFILE_CONFIG['roles'].items() if v['language'] == 'en')
SYMBOL_ROLES = frozenset(k for k, v in PROFILE_CONFIG['roles'].items() if v['language'] == 'preserve')
HAN = re.compile('[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003134f]')


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ('br', 'p', 'div', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag.lower() in ('p', 'div', 'li'):
            self.parts.append(' ')


def plain_text(value, is_html=False):
    """Read label markup without running scripts or changing source content."""
    if not is_html:
        return ' '.join(value.split())
    parser = _PlainText()
    parser.feed(value)
    parser.close()
    return ' '.join(''.join(parser.parts).split())


def check_document(doc, format='report', profile=PROFILE):
    """Return finite contract checks. Always require separate semantic review.

    All supplied visible text objects need explicit text_role. Geometry, box
    membership and semantic-node metadata never infer the role. Surrounding text
    is checked when supplied, but completeness against a render is not verified.
    """
    errors, warnings, items = [], [], []
    if profile != PROFILE:
        errors.append(f'Unsupported language profile: {profile!r}')
    if format not in ('report', 'model'):
        errors.append(f'Unsupported format: {format!r}')
    declared = None
    counts = {'source_texts': 0, 'surrounding_texts': 0, 'checked_texts': 0,
              'unclassified_texts': 0, 'empty_texts': 0, 'wrapper_texts': 0,
              'rendered_coverage': 'not_verified'}

    def add(identifier, value, role, surrounding=False, is_html=False, wrapped=False):
        if not isinstance(value, str):
            errors.append(f'{identifier}: text must be a string')
            return
        text = plain_text(value, is_html=is_html)
        if not text:
            counts['empty_texts'] += 1
            return
        counts['surrounding_texts' if surrounding else 'source_texts'] += 1
        if wrapped:
            counts['wrapper_texts'] += 1
        items.append((identifier, text, role))

    def list_of_objects(value, location):
        if not isinstance(value, list):
            errors.append(f'{location}: expected an array')
            return []
        valid = []
        for i, obj in enumerate(value):
            if not isinstance(obj, dict):
                errors.append(f'{location}[{i}]: expected an object')
            else:
                valid.append(obj)
        return valid

    if format == 'report':
        if not isinstance(doc, dict):
            errors.append('Report input must be an object')
        else:
            declared = doc.get('language_profile')
            for vi, view in enumerate(list_of_objects(doc.get('views', []), 'views')):
                prefix = str(view.get('id', f'view[{vi}]'))
                if not isinstance(view.get('title'), str) or not plain_text(view.get('title', '')):
                    errors.append(f'{prefix}: a nonempty view title with title_text_role is required')
                else:
                    add(prefix + '/title', view['title'], view.get('title_text_role'), surrounding=True)
                if 'scope' in view:
                    add(prefix + '/scope', view['scope'], view.get('scope_text_role'), surrounding=True)
                for gi, glyph in enumerate(list_of_objects(view.get('glyphs', []), prefix + '.glyphs')):
                    ident = prefix + '/' + str(glyph.get('id', f'glyph[{gi}]'))
                    if 'label_lines' in glyph:
                        lines = glyph['label_lines']
                        if not isinstance(lines, list) or not all(isinstance(v, str) for v in lines):
                            errors.append(f'{ident}: label_lines must be an array of strings')
                            continue
                        label = '\n'.join(lines)
                    else:
                        label = glyph.get('label', '')
                    add(ident, label, glyph.get('text_role'))
                for pi, path in enumerate(list_of_objects(view.get('paths', []), prefix + '.paths')):
                    add(prefix + '/' + str(path.get('id', f'path[{pi}]')),
                        path.get('label', ''), path.get('text_role'))
            for i, text in enumerate(list_of_objects(doc.get('surrounding_texts', []), 'surrounding_texts')):
                add('surrounding/' + str(text.get('id', i)), text.get('text', ''),
                    text.get('text_role'), surrounding=True)
    elif format == 'model':
        try:
            if isinstance(doc, ET.Element):
                root = doc
            elif isinstance(doc, (str, bytes)):
                raw = doc.encode('utf-8') if isinstance(doc, str) else doc
                if re.search(br'<!\s*(?:DOCTYPE|ENTITY)\b', raw, re.I):
                    raise ValueError('DTD/entity declarations are not supported')
                root = ET.fromstring(raw)
            else:
                raise ValueError('Model input must be uncompressed draw.io XML')
            declared = root.get('language_profile')
            cells = list(root.iter('mxCell'))
            if not cells:
                errors.append('No mxCell objects found; compressed/unsupported draw.io is not checked')
            parents = {child: parent for parent in root.iter() for child in parent}
            for i, cell in enumerate(cells):
                parent = parents.get(cell)
                wrapper = parent if parent is not None and parent.tag in ('object', 'UserObject') else None
                is_html = bool(re.search(r'(?:^|;)html=1(?:;|$)', cell.get('style', '')))
                wrapper_role = wrapper.get('text_role') if wrapper is not None else None
                cell_role = cell.get('text_role')
                if wrapper_role is not None and cell_role is not None and wrapper_role != cell_role:
                    errors.append(f'cell/{cell.get("id", i)}: wrapper and mxCell text_role conflict')
                # Wrapper role has priority; the child role is an explicit fallback.
                # Check a nonempty child value too, conservatively, rather than
                # silently discarding another supplied label in an unusual file.
                role = wrapper_role if wrapper_role is not None else cell_role
                if wrapper is not None and 'label' in wrapper.attrib:
                    add('wrapper/' + str(wrapper.get('id', cell.get('id', i))),
                        wrapper.get('label', ''), role, is_html=is_html, wrapped=True)
                add('cell/' + str(cell.get('id', i)), cell.get('value', ''), role, is_html=is_html)
        except (ET.ParseError, ValueError) as exc:
            errors.append(f'Model XML: {exc}')
    if declared is not None and declared != profile:
        errors.append(f'Source language_profile {declared!r} does not match requested {profile!r}')
    for identifier, text, role in items:
        if not isinstance(role, str) or role not in TEXT_ROLES:
            errors.append(f'{identifier}: missing or invalid text_role {role!r}')
            counts['unclassified_texts'] += 1
            continue
        counts['checked_texts'] += 1
        if role in ENGLISH_ROLES and HAN.search(text):
            errors.append(f'{identifier}: {role} contains Han characters; English functional labels required')
        elif role in CONTEXT_ROLES and not HAN.search(text):
            warnings.append(f'{identifier}: {role} has no Han characters; review Chinese explanation or reclassify a genuine standalone term/symbol')
    if not items:
        warnings.append('No nonempty text found; rendered text coverage is not verified')
    return {'profile': profile, 'input_sha256': None,
            'status': 'fail' if errors else 'needs_review',
            'contract_status': 'fail' if errors else 'pass',
            'semantic_review': 'not_run', 'coverage': counts,
            'errors': errors, 'warnings': warnings,
            'limits': ['Explicit roles are author declarations, not semantic verification.',
                       'Character checks do not prove English/Chinese language or terminology correctness.',
                       'Text absent from this source, including surrounding layout text, requires rendered coverage review.',
                       'No automatic translation or technical text rewriting is performed.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--format', choices=('report', 'model'), required=True)
    parser.add_argument('--profile', default=PROFILE)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        doc = json.loads(raw) if args.format == 'report' else raw
        result = check_document(doc, args.format, args.profile)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    result['input_sha256'] = hashlib.sha256(raw).hexdigest()
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content)
    else:
        print(content, end='')
    return 1 if result['contract_status'] == 'fail' else 0


if __name__ == '__main__':
    sys.exit(main())
