#!/usr/bin/env python3
"""Check diagram delivery evidence contracts, not semantic or visual correctness."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import subprocess
import tempfile
from xml.etree import ElementTree as ET

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
BRIEF_SCHEMA = ROOT / 'contracts/diagram-brief.schema.json'
DELIVERY_SCHEMA = ROOT / 'contracts/diagram-delivery.schema.json'


def _schema_errors(value, schema_path, label):
    schema = json.loads(schema_path.read_text())
    Draft202012Validator.check_schema(schema)
    errors = Draft202012Validator(schema).iter_errors(value)
    return [f'{label}/{"/".join(str(x) for x in e.absolute_path)}: {e.message}'
            for e in sorted(errors, key=lambda e: str(list(e.absolute_path)))]


def _relative_parts(name):
    # Repository contracts use portable POSIX paths, not URLs or Windows drives.
    if not name or '\\' in name or ':' in name:
        raise ValueError('artifact path must be a portable relative path')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('artifact path may not be absolute, empty, dot or parent traversal')
    return path.parts


def _read_artifact(root_fd, name):
    """Read through descriptor-relative, no-follow opens; reject all symlink components."""
    parts = _relative_parts(name)
    current = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = nxt
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=current)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('artifact must be a regular file')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                return stream.read()
        finally:
            os.close(fd)
    finally:
        os.close(current)


def _drawing_ids(data, name):
    """Extract object identifiers only; this does not assess their semantic role."""
    if name.lower().endswith('.json'):
        doc = json.loads(data)
        if not isinstance(doc, dict) or not isinstance(doc.get('views'), list):
            return set()
        result = set()
        for view in doc['views']:
            if not isinstance(view, dict):
                continue
            for collection in ('glyphs', 'paths'):
                for obj in view.get(collection, []):
                    if isinstance(obj, dict) and isinstance(obj.get('id'), str):
                        result.add(obj['id'])
                        if isinstance(view.get('id'), str):
                            result.add(view['id'] + '/' + obj['id'])
        return result
    if name.lower().endswith(('.drawio', '.xml', '.svg')):
        if re.search(br'<!\s*(?:DOCTYPE|ENTITY)\b', data, re.I):
            raise ValueError('DTD/entity declarations are unsupported in editable XML')
        root = ET.fromstring(data)
        return {e.attrib['id'] for e in root.iter() if e.attrib.get('id')}
    return set()


def _pdf_pages(raw):
    """Parse the exact verified bytes, never a mutable original artifact path."""
    if not raw.startswith(b'%PDF-'):
        raise ValueError('archive PDF lacks PDF magic')
    with tempfile.TemporaryDirectory(prefix='diagram-pdf-') as folder:
        pdf = Path(folder) / 'archive.pdf'
        pdf.write_bytes(raw)
        info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, timeout=20,
                              env={**os.environ, 'LC_ALL': 'C'})
        if info.returncode:
            raise ValueError('archive PDF cannot be parsed by pdfinfo')
        match = re.search(rb'^Pages:\s*(\d+)\s*$', info.stdout, re.M)
        if not match or int(match[1]) < 1:
            raise ValueError('archive PDF has no parseable page count')
        count = int(match[1])
        if count > 256:
            raise ValueError('archive PDF exceeds checker limit of 256 pages')
        text = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True,
                              timeout=20, env={**os.environ, 'LC_ALL': 'C'})
        if text.returncode:
            raise ValueError('archive PDF text extraction failed')
        pages = text.stdout.decode('utf-8', errors='replace').split('\f')
        if pages and not pages[-1].strip():
            pages.pop()
        if len(pages) != count:
            raise ValueError('archive PDF extracted page count does not match pdfinfo')
        return pages


def check_delivery(brief_path, delivery_path, artifact_root):
    """Validate local schemas, exact byte bindings and evidence references.

    A pass is mechanical only. Files and declarations cannot prove that someone
    read a reference, ran an engine, or inspected a rendered result.
    """
    errors, warnings, verified = [], [], []
    result = {'status': 'fail', 'contract_status': 'fail',
              'semantic_visual_status': 'not_verified', 'brief_sha256': None,
              'delivery_sha256': None, 'artifacts': verified,
              'errors': errors, 'warnings': warnings,
              'limits': ['Hashes bind supplied bytes, not evidence of reading or actual rendering.',
                         'Object ID membership does not prove a selected design was correctly applied.',
                         'Review declarations are not independent semantic or visual verification.',
                         'Required output extensions establish file presence, not format validity.']}
    try:
        brief_raw = Path(brief_path).read_bytes()
        delivery_raw = Path(delivery_path).read_bytes()
        result['brief_sha256'] = hashlib.sha256(brief_raw).hexdigest()
        result['delivery_sha256'] = hashlib.sha256(delivery_raw).hexdigest()
        brief, delivery = json.loads(brief_raw), json.loads(delivery_raw)
        errors.extend(_schema_errors(brief, BRIEF_SCHEMA, 'brief'))
        errors.extend(_schema_errors(delivery, DELIVERY_SCHEMA, 'delivery'))
    except (OSError, ValueError) as exc:
        errors.append(f'Input/schema could not be read: {exc}')
        return result
    if errors:
        return result
    if delivery['brief_sha256'] != result['brief_sha256']:
        errors.append('delivery.brief_sha256 does not bind the exact supplied brief bytes')
    for field in ('task_id', 'intent'):
        if delivery[field] != brief[field]:
            errors.append(f'delivery.{field} does not match brief.{field}')
    for ref in delivery['references']:
        if not ref['observations'].strip():
            errors.append('reference observations must not be blank')
    for field in ('observations', 'reference_comparison'):
        if not delivery['visual_review'][field].strip():
            errors.append(f'visual_review.{field} must not be blank')
    result['task_id'] = delivery['task_id']
    result['intent'] = delivery['intent']
    result['delivery_status'] = delivery['status']
    result['stages'] = {'references': [r['status'] for r in delivery['references']],
                        'render': delivery['render']['status'],
                        'visual_review': delivery['visual_review']['status']}
    artifacts = {}
    artifact_bytes = {}
    paths = set()
    root_fd = None
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY') or os.open not in os.supports_dir_fd:
        errors.append('Platform cannot enforce descriptor-relative no-symlink artifact checks')
        return result
    try:
        root = Path(artifact_root)
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for artifact in delivery['artifacts']:
            aid, name = artifact['id'], artifact['path']
            if aid in artifacts:
                errors.append(f'duplicate artifact id: {aid}')
                continue
            artifacts[aid] = artifact
            if name in paths:
                errors.append(f'duplicate artifact path: {name}')
            paths.add(name)
            try:
                raw = _read_artifact(root_fd, name)
                digest = hashlib.sha256(raw).hexdigest()
                if digest != artifact['sha256']:
                    errors.append(f'artifact {aid}: SHA-256 mismatch')
                    continue
                artifact_bytes[aid] = raw
                verified.append({**artifact, 'verification': 'sha256_verified', 'size_bytes': len(raw)})
            except (OSError, ValueError) as exc:
                errors.append(f'artifact {aid}: unsafe/unreadable path: {exc}')
    except OSError as exc:
        errors.append(f'Artifact root unavailable or a symlink: {exc}')
    finally:
        if root_fd is not None:
            os.close(root_fd)

    def linked(aid, location, expected_kind=None):
        if aid not in artifacts:
            errors.append(f'{location}: unknown artifact id {aid!r}')
            return False
        if aid not in artifact_bytes:
            errors.append(f'{location}: artifact {aid!r} was not byte-verified')
            return False
        if expected_kind and artifacts[aid]['kind'] != expected_kind:
            errors.append(f'{location}: artifact {aid!r} must have kind {expected_kind}')
            return False
        return True

    reference_ids = set()
    for ref in delivery['references']:
        if ref['id'] in reference_ids:
            errors.append(f'duplicate reference id: {ref["id"]}')
        reference_ids.add(ref['id'])
        if ref.get('artifact_id'):
            linked(ref['artifact_id'], f'reference {ref["id"]}', 'reference')
        elif ref['status'] == 'reviewed':
            errors.append(f'reference {ref["id"]}: reviewed reference needs a byte-bound artifact')
    render = delivery['render']
    visual = delivery['visual_review']
    for aid in render['artifact_ids']:
        linked(aid, 'render', 'rendered')
    if render.get('qa_artifact_id'):
        linked(render['qa_artifact_id'], 'render.qa_artifact_id', 'qa')
    for aid in visual['artifact_ids']:
        linked(aid, 'visual_review', 'rendered')
        if aid not in render['artifact_ids']:
            errors.append(f'visual_review: {aid!r} is not one of the declared render artifacts')
    for revision in delivery['revisions']:
        for aid in revision['evidence_artifact_ids']:
            linked(aid, 'revision evidence')
    if render['status'] == 'rendered' and not render['artifact_ids']:
        errors.append('render.status rendered requires rendered artifacts')
    if visual['status'] == 'reviewed' and not visual['artifact_ids']:
        errors.append('visual_review.status reviewed requires rendered artifacts')

    if delivery['intent'] in ('report', 'mixed'):
        design = delivery['design']
        selected = design.get('selected_options', [])
        selector_id = design.get('selector_artifact_id')
        applications = design.get('selection_applications', [])
        selection_required = delivery['status'] == 'completed'
        selector_available = False
        if selector_id:
            selector_available = linked(selector_id, 'design.selector_artifact_id', 'selector')
        if not selector_available and (selection_required or selected or applications):
            errors.append('report/mixed design requires a byte-verified selector artifact')
        if selector_available:
            try:
                selector = json.loads(artifact_bytes[selector_id])
                if not isinstance(selector, dict) or not isinstance(selector.get('options'), list):
                    raise ValueError('selector must contain an options array')
                if selector.get('task_id') != brief['task_id']:
                    errors.append('selector.task_id does not match brief.task_id')
                options = selector['options']
                if any(not isinstance(o, dict) or not isinstance(o.get('rule_id'), str) for o in options):
                    raise ValueError('selector options must contain string rule_id values')
                candidates = {o['rule_id'] for o in options}
                if len(candidates) != len(options):
                    errors.append('selector contains duplicate rule_id candidates')
                for option in selected:
                    if option not in candidates:
                        errors.append(f'selected option {option!r} is absent from selector candidates')
            except (ValueError, KeyError) as exc:
                errors.append(f'selector artifact invalid: {exc}')
        if (selection_required and not selected) or len(set(selected)) != len(selected):
            errors.append('report/mixed selected_options must be nonempty and unique')
        if (selection_required or selected) and not str(design.get('selection_reason', '')).strip():
            errors.append('report/mixed design requires selection_reason')
        if selection_required and not applications:
            errors.append('report/mixed design requires selection_applications')
        object_ids = set()
        for aid, raw in artifact_bytes.items():
            if artifacts[aid]['kind'] == 'editable_source':
                try:
                    object_ids.update(_drawing_ids(raw, artifacts[aid]['path']))
                except (ValueError, ET.ParseError, TypeError) as exc:
                    errors.append(f'editable source {aid}: cannot read drawing object IDs: {exc}')
        mapped = set()
        for application in applications:
            option = application['option_id']
            mapped.add(option)
            if option not in selected:
                errors.append(f'selection application {option!r} is not a selected option')
            for oid in application['drawing_object_ids']:
                if oid not in object_ids:
                    errors.append(f'selection application: drawing object {oid!r} absent from verified editable sources')
        if selection_required and set(selected) - mapped:
            errors.append('each selected option requires a selection application')

    variants = delivery.get('variants', [])
    completed = delivery['status'] == 'completed'
    if completed and len(variants) != brief.get('variant_count', 3):
        errors.append('completed delivery variants count must match brief.variant_count (default 3)')
    variant_ids = set()
    used_pages = set()
    archive_id = delivery.get('archive_pdf_artifact_id')
    pdf_pages = None
    if archive_id and linked(archive_id, 'archive_pdf_artifact_id'):
        if artifacts[archive_id]['kind'] not in ('rendered', 'other'):
            errors.append('archive_pdf_artifact_id must have kind rendered or other')
        try:
            pdf_pages = _pdf_pages(artifact_bytes[archive_id])
            result['archive_pdf'] = {'artifact_id': archive_id, 'page_count': len(pdf_pages),
                                     'verification': 'parsed', 'numbering_status': 'pending'}
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            errors.append(f'archive PDF: {exc}')
    elif completed:
        errors.append('completed delivery requires a byte-bound archive_pdf_artifact_id')
    numbering_errors_before = len(errors)
    used_sources, used_renders = set(), set()
    rendered_signature_owners = {}
    for variant in variants:
        vid = variant['id']
        if vid in variant_ids:
            errors.append(f'duplicate variant id: {vid}')
        variant_ids.add(vid)
        if not variant['structural_difference'].strip():
            errors.append(f'variant {vid}: structural_difference must not be blank')
        for field, kind, used in [('editable_artifact_ids', 'editable_source', used_sources),
                                  ('rendered_artifact_ids', 'rendered', used_renders)]:
            ids = variant[field]
            if not ids or len(ids) != len(set(ids)):
                errors.append(f'variant {vid}: {field} must be nonempty and unique')
            for aid in ids:
                linked(aid, f'variant {vid}.{field}', kind)
                if aid in used:
                    errors.append(f'variant {vid}: {field} reuses another variant artifact {aid}')
                used.add(aid)
                if field == 'rendered_artifact_ids' and aid not in render['artifact_ids']:
                    errors.append(f'variant {vid}: rendered artifact absent from render.artifact_ids')
                if field == 'rendered_artifact_ids' and completed and aid not in visual['artifact_ids']:
                    errors.append(f'variant {vid}: rendered artifact absent from visual_review.artifact_ids')
        rendered_ids = variant['rendered_artifact_ids']
        if rendered_ids and all(aid in artifact_bytes for aid in rendered_ids):
            signature = frozenset(hashlib.sha256(artifact_bytes[aid]).hexdigest() for aid in rendered_ids)
            if signature in rendered_signature_owners:
                errors.append(f'variant {vid}: rendered SHA set identical to variant {rendered_signature_owners[signature]}')
            else:
                rendered_signature_owners[signature] = vid
        linked(variant['qa_artifact_id'], f'variant {vid}.qa_artifact_id', 'qa')
        for page in variant['pdf_pages']:
            if page in used_pages:
                errors.append(f'variant {vid}: PDF page {page} assigned more than once')
            used_pages.add(page)
            if pdf_pages is not None:
                if page < 1 or page > len(pdf_pages):
                    errors.append(f'variant {vid}: PDF page {page} out of range')
                elif not re.search(r'(?<![\w-])' + re.escape(vid) + r'(?![\w-])', pdf_pages[page - 1]):
                    errors.append(f'variant {vid}: PDF page {page} lacks extractable variant ID')
    if pdf_pages is not None and used_pages != set(range(1, len(pdf_pages) + 1)):
        errors.append('archive PDF pages must all be assigned exactly once to variants')
    if pdf_pages is not None:
        result['archive_pdf']['numbering_status'] = 'pass' if len(errors) == numbering_errors_before else 'fail'
    if delivery.get('selected_variant_id') is not None and delivery['selected_variant_id'] not in variant_ids:
        errors.append('selected_variant_id must name an existing variant')
    result['limits'].append('PDF parsing and extractable variant IDs do not prove visible placement, distinct layouts or aesthetic quality; different rendered hashes do not prove substantive visual differences.')

    if delivery['status'] == 'completed':
        if not render.get('qa_artifact_id'):
            errors.append('completed delivery requires render.qa_artifact_id bound to QA evidence')
        if not delivery['references'] or any(r['status'] != 'reviewed' for r in delivery['references']):
            errors.append('completed delivery requires reviewed references and no unavailable references')
        if render['status'] != 'rendered' or visual['status'] != 'reviewed':
            errors.append('completed delivery requires rendered output and reviewed visual status')
        for kind in ('editable_source', 'rendered'):
            if not any(a['kind'] == kind for a in artifacts.values()):
                errors.append(f'completed delivery requires at least one {kind} artifact')
        output_extensions = {PurePosixPath(artifacts[aid]['path']).suffix.lower().lstrip('.')
                             for aid in artifact_bytes
                             if artifacts[aid]['kind'] in ('editable_source', 'rendered', 'other')}
        for extension in set(brief['required_outputs']):
            if extension not in output_extensions:
                errors.append(f'completed delivery is missing required output extension: {extension}')
    elif not delivery['limitations']:
        errors.append('blocked delivery must record limitations')
    if not delivery['revisions']:
        warnings.append('No revision evidence; visual review observations must explain why no fix was needed.')
    if not errors:
        result['status'] = 'needs_review'
        result['contract_status'] = 'pass'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brief', type=Path, required=True)
    parser.add_argument('--delivery', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check_delivery(args.brief, args.delivery, args.root)
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        protected = {args.brief.resolve(), args.delivery.resolve()}
        protected.update((args.root / a['path']).resolve() for a in result['artifacts'])
        if args.output.resolve() in protected:
            parser.error('--output cannot overwrite an input or verified artifact')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end='')
    return 0 if result['contract_status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
