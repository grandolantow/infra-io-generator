import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/check_diagram_delivery.py'
spec = importlib.util.spec_from_file_location('diagram_delivery_checker', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def make_pdf(labels):
    """Small real PDF fixture with a Helvetica text stream per page; no optional dependency."""
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids = []
    for label in labels:
        page_id = len(objects) + 1
        kids.append(f'{page_id} 0 R')
        stream = f'BT /F1 18 Tf 50 700 Td ({label}) Tj ET'.encode('ascii')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id+1} 0 R >>'.encode())
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
    raw = b'%PDF-1.4\n'; offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(raw)); raw += f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(raw)
    raw += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    raw += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    raw += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return raw


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact_root = self.root / 'artifacts'
        self.artifact_root.mkdir()
        self.brief_path = self.root / 'brief.json'
        self.delivery_path = self.root / 'delivery.json'
        self.brief = {'schema_version': 1, 'task_id': 'toy', 'intent': 'report',
                      'question': 'Explain logical page mapping', 'audience': 'Engineers',
                      'facts': [{'id': 'f1', 'statement': 'Toy maps L0 to P1', 'status': 'verified',
                                 'sources': ['invented toy']}], 'target': 'standalone',
                      'theme': {}, 'display_constraints': {}, 'required_outputs': ['drawio', 'svg'],
                      'language_profile': 'diagram-en-prose-zh', 'preserve': []}
        self.brief_path.write_text(json.dumps(self.brief))
        files = [
            ('ref', 'reference.txt', 'reference', b'Public design note used as toy fixture'),
            ('selector', 'selector.json', 'selector', json.dumps({'task_id': 'toy', 'options': [{'rule_id': 'S04'}]}).encode()),
            ('source', 'drawing.drawio', 'editable_source', b'<mxfile><mxCell id="page-L0"/><mxCell id="mapping-edge"/></mxfile>'),
            ('render', 'drawing.svg', 'rendered', b'<svg xmlns="http://www.w3.org/2000/svg"><text>Mapping</text></svg>'),
            ('qa', 'render-qa.json', 'qa', b'{"scope":"test fixture only","status":"not_verified"}')]
        artifacts = []
        for aid, name, kind, raw in files:
            (self.artifact_root / name).write_bytes(raw)
            artifacts.append({'id': aid, 'path': name, 'sha256': digest(raw), 'kind': kind})
        self.delivery = {'schema_version': 1, 'task_id': 'toy', 'intent': 'report',
                         'brief_sha256': digest(self.brief_path.read_bytes()), 'status': 'completed',
                         'artifacts': artifacts,
                         'references': [{'id': 'r1', 'location': 'https://example.org/public-paper',
                                         'role': 'public_source', 'status': 'reviewed',
                                         'observations': 'Diagram contrasts logical identity with physical placement.',
                                         'artifact_id': 'ref'}],
                         'design': {'semantic_summary': 'Toy identity mapping', 'components': 'Page blocks',
                                    'proportions': 'Equal page blocks', 'connections': 'One mapping edge',
                                    'typography': 'Readable labels', 'surrounding_texts': 'Short caption',
                                    'layout_decision': {}, 'reference_comparison': 'Shared identity labels',
                                    'selector_artifact_id': 'selector', 'selected_options': ['S04'],
                                    'selection_reason': 'Mapping keeps identity visible',
                                    'selection_applications': [{'option_id': 'S04', 'drawing_object_ids': ['page-L0'],
                                                                'application': 'Native page object exposes identity'}]},
                         'render': {'status': 'rendered', 'backend': 'test fixture', 'artifact_ids': ['render'], 'qa_artifact_id': 'qa'},
                         'visual_review': {'status': 'reviewed', 'artifact_ids': ['render'], 'reviewer': 'agent',
                                           'observations': 'Toy fixture: no correction required for this declared review.',
                                           'reference_comparison': 'Both identities are visible in the declared example.'},
                         'revisions': [], 'limitations': ['Fixture contract only, not actual visual inspection.']}

        self.delivery['variants'] = []
        for i in range(1, 4):
            if i == 1:
                source_id, render_id = 'source', 'render'
            else:
                source_id, render_id = f'source{i}', f'render{i}'
                self.add_artifact(source_id, f'drawing{i}.drawio', 'editable_source', files[2][3])
                self.add_artifact(render_id, f'drawing{i}.svg', 'rendered', files[3][3].replace(b'Mapping', f'Mapping variant {i}'.encode()))
                self.delivery['render']['artifact_ids'].append(render_id)
                self.delivery['visual_review']['artifact_ids'].append(render_id)
            self.delivery['variants'].append({'id': f'V{i}', 'structural_difference': f'Fixture layout {i}',
                'editable_artifact_ids': [source_id], 'rendered_artifact_ids': [render_id],
                'qa_artifact_id': 'qa', 'pdf_pages': [i]})
        self.add_artifact('archive', 'archive.pdf', 'other', make_pdf(['V1', 'V2', 'V3']))
        self.delivery['archive_pdf_artifact_id'] = 'archive'

    def add_artifact(self, aid, name, kind, raw):
        (self.artifact_root / name).write_bytes(raw)
        self.delivery['artifacts'].append({'id': aid, 'path': name, 'kind': kind, 'sha256': digest(raw)})

    def replace_archive(self, raw):
        (self.artifact_root / 'archive.pdf').write_bytes(raw)
        next(a for a in self.delivery['artifacts'] if a['id'] == 'archive')['sha256'] = digest(raw)

    def check(self):
        self.delivery_path.write_text(json.dumps(self.delivery))
        return checker.check_delivery(self.brief_path, self.delivery_path, self.artifact_root)

    def assert_bad(self, needle):
        result = self.check()
        self.assertEqual(result['contract_status'], 'fail', result)
        self.assertTrue(any(needle in e for e in result['errors']), result['errors'])

    def test_valid_contract_is_not_semantic_or_visual_proof(self):
        result = self.check()
        self.assertEqual(result['contract_status'], 'pass', result['errors'])
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(result['semantic_visual_status'], 'not_verified')
        self.assertEqual(len(result['artifacts']), 10)
        self.assertTrue(result['warnings'])

    def test_exact_brief_bytes_bound(self):
        self.brief_path.write_bytes(self.brief_path.read_bytes() + b'\n')
        self.assert_bad('brief_sha256')

    def test_schema_validation(self):
        del self.delivery['visual_review']['observations']
        self.assert_bad('observations')

    def test_task_and_intent_match(self):
        for field, value in [('task_id', 'wrong'), ('intent', 'mixed')]:
            original = self.delivery[field]
            self.delivery[field] = value
            self.assert_bad('does not match brief')
            self.delivery[field] = original

    def test_artifact_hash_tampering(self):
        (self.artifact_root / 'drawing.svg').write_bytes(b'tampered')
        self.assert_bad('SHA-256 mismatch')

    def test_path_traversal_absolute_and_nonportable(self):
        for name in ['../outside', '/tmp/outside', 'x/../outside', './drawing.svg', 'C:\\drawing.svg', 'a//b']:
            self.delivery['artifacts'][3]['path'] = name
            self.assert_bad('unsafe/unreadable path')

    def test_file_and_directory_symlinks_rejected(self):
        source = self.artifact_root / 'drawing.svg'
        source.rename(self.root / 'outside.svg')
        source.symlink_to(self.root / 'outside.svg')
        self.assert_bad('unsafe/unreadable path')
        source.unlink()
        directory = self.artifact_root / 'linked'
        directory.symlink_to(self.root, target_is_directory=True)
        self.delivery['artifacts'][3]['path'] = 'linked/outside.svg'
        self.assert_bad('unsafe/unreadable path')

    def test_root_symlink_rejected(self):
        link = self.root / 'root-link'; link.symlink_to(self.artifact_root, target_is_directory=True)
        self.delivery_path.write_text(json.dumps(self.delivery))
        result = checker.check_delivery(self.brief_path, self.delivery_path, link)
        self.assertEqual(result['contract_status'], 'fail')
        self.assertTrue(any('root unavailable' in e for e in result['errors']))

    def test_duplicate_artifact_identity(self):
        self.delivery['artifacts'].append(copy.deepcopy(self.delivery['artifacts'][0]))
        self.assert_bad('duplicate artifact id')

    def test_reference_must_have_real_bound_artifact(self):
        self.delivery['references'][0]['artifact_id'] = 'missing'
        self.assert_bad('unknown artifact')

    def test_completed_cannot_hide_unavailable_reference(self):
        self.delivery['references'][0]['status'] = 'unavailable'
        self.assert_bad('reviewed references')

    def test_completed_requires_render_and_visual_review(self):
        for stage, value in [('render', 'blocked'), ('visual_review', 'not_run')]:
            old = self.delivery[stage]['status']; self.delivery[stage]['status'] = value
            self.assert_bad('requires rendered output')
            self.delivery[stage]['status'] = old

    def test_render_link_requires_rendered_kind(self):
        self.delivery['render']['artifact_ids'] = ['source']
        self.assert_bad('must have kind rendered')

    def test_review_cannot_reference_unrendered_object(self):
        self.delivery['visual_review']['artifact_ids'] = ['ref']
        self.assert_bad('not one of the declared render artifacts')

    def test_selector_option_ids_are_real_rule_ids(self):
        self.delivery['design']['selected_options'] = ['invented']
        self.assert_bad('absent from selector candidates')

    def test_selector_task_binding(self):
        raw = json.dumps({'task_id': 'other', 'options': [{'rule_id': 'S04'}]}).encode()
        (self.artifact_root / 'selector.json').write_bytes(raw)
        self.delivery['artifacts'][1]['sha256'] = digest(raw)
        self.assert_bad('selector.task_id')

    def test_selector_json_not_just_an_assertion(self):
        (self.artifact_root / 'selector.json').write_bytes(b'not json')
        self.delivery['artifacts'][1]['sha256'] = digest(b'not json')
        self.assert_bad('selector artifact invalid')

    def test_application_references_real_editable_object(self):
        self.delivery['design']['selection_applications'][0]['drawing_object_ids'] = ['invented-object']
        self.assert_bad('absent from verified editable sources')

    def test_each_option_requires_application(self):
        del self.delivery['design']['selection_applications']
        self.assert_bad('requires selection_applications')

    def test_report_ir_object_ids_supported(self):
        raw = json.dumps({'views': [{'id': 'view', 'glyphs': [{'id': 'page-L0'}], 'paths': []}]}).encode()
        source = self.delivery['artifacts'][2]
        source['path'] = 'source.json'; source['sha256'] = digest(raw)
        (self.artifact_root / 'source.json').write_bytes(raw)
        self.delivery['design']['selection_applications'][0]['drawing_object_ids'] = ['view/page-L0']
        self.brief['required_outputs'] = ['svg']
        self.brief_path.write_text(json.dumps(self.brief))
        self.delivery['brief_sha256'] = digest(self.brief_path.read_bytes())
        self.assertEqual(self.check()['contract_status'], 'pass')

    def test_blocked_before_render_is_truthful(self):
        self.delivery['status'] = 'blocked'
        self.delivery.pop('variants', None)
        self.delivery.pop('archive_pdf_artifact_id', None)
        self.delivery['artifacts'] = self.delivery['artifacts'][:1]
        self.delivery['render'] = {'status': 'blocked', 'backend': 'unavailable', 'artifact_ids': []}
        self.delivery['visual_review']['status'] = 'not_run'
        self.delivery['visual_review']['artifact_ids'] = []
        for field in ['selector_artifact_id', 'selected_options', 'selection_reason', 'selection_applications']:
            self.delivery['design'].pop(field)
        self.assertEqual(self.check()['contract_status'], 'pass')
        self.delivery['limitations'] = []
        self.assert_bad('blocked delivery must record limitations')

    def test_completed_needs_bound_render_qa(self):
        del self.delivery['render']['qa_artifact_id']
        self.assert_bad('requires render.qa_artifact_id')

    def test_empty_blocked_delivery_does_not_fabricate_outputs(self):
        self.delivery['status'] = 'blocked'
        self.delivery.pop('variants', None)
        self.delivery.pop('archive_pdf_artifact_id', None)
        self.delivery['artifacts'] = []
        self.delivery['references'][0]['status'] = 'unavailable'
        del self.delivery['references'][0]['artifact_id']
        self.delivery['render'] = {'status': 'blocked', 'backend': 'unavailable', 'artifact_ids': []}
        self.delivery['visual_review']['status'] = 'not_run'
        self.delivery['visual_review']['artifact_ids'] = []
        for field in ['selector_artifact_id', 'selected_options', 'selection_reason', 'selection_applications']:
            self.delivery['design'].pop(field)
        self.assertEqual(self.check()['contract_status'], 'pass')

    def test_actual_selector_output_and_report_source_ids(self):
        package = ROOT / 'skills/technical-diagram-options'
        task = json.loads((package / 'examples/toy-mapping.task.json').read_text())
        task['task_id'] = 'toy'
        task_path = self.root / 'selector-task.json'; task_path.write_text(json.dumps(task))
        output = self.artifact_root / 'selector.json'
        subprocess.run([sys.executable, str(package / 'scripts/select_options.py'), str(task_path),
                        '--out', str(output)], check=True, capture_output=True)
        actual = json.loads(output.read_text())
        self.assertTrue(actual['options'])
        option = actual['options'][0]['rule_id']
        self.delivery['artifacts'][1]['sha256'] = digest(output.read_bytes())
        source = (package / 'examples/toy-mapping.diagram.json').read_bytes()
        (self.artifact_root / 'source.json').write_bytes(source)
        self.delivery['artifacts'][2].update(path='source.json', sha256=digest(source))
        source_doc = json.loads(source)
        oid = source_doc['views'][0]['glyphs'][0]['id']
        self.delivery['design']['selected_options'] = [option]
        self.brief['required_outputs'] = ['svg']
        self.brief_path.write_text(json.dumps(self.brief))
        self.delivery['brief_sha256'] = digest(self.brief_path.read_bytes())
        self.delivery['design']['selection_applications'] = [
            {'option_id': option, 'drawing_object_ids': [oid], 'application': 'Contract fixture uses an existing source object.'}]
        self.assertEqual(self.check()['contract_status'], 'pass')

    def test_completed_requires_requested_output_extensions(self):
        self.brief['required_outputs'].append('html')
        self.brief_path.write_text(json.dumps(self.brief))
        self.delivery['brief_sha256'] = digest(self.brief_path.read_bytes())
        self.assert_bad('missing required output extension: html')
        raw = b'Fixture bytes: extension check is not PDF format verification'
        (self.artifact_root / 'result.html').write_bytes(raw)
        self.delivery['artifacts'].append({'id': 'pdf', 'path': 'result.html', 'sha256': digest(raw), 'kind': 'other'})
        self.assertEqual(self.check()['contract_status'], 'pass')

    def test_reference_file_does_not_count_as_required_output(self):
        self.brief['required_outputs'].append('html')
        self.brief_path.write_text(json.dumps(self.brief))
        self.delivery['brief_sha256'] = digest(self.brief_path.read_bytes())
        raw = b'Fixture reference PDF, not a delivered figure'
        (self.artifact_root / 'reference.html').write_bytes(raw)
        self.delivery['artifacts'].append({'id': 'pdf-reference', 'path': 'reference.html', 'sha256': digest(raw), 'kind': 'reference'})
        self.assert_bad('missing required output extension: html')

    def test_empty_review_is_not_evidence(self):
        self.delivery['visual_review']['observations'] = ' '
        self.assert_bad('must not be blank')

    def test_cli_json_and_exit_status(self):
        self.check()
        output = self.root / 'qa.json'
        command = [sys.executable, str(SCRIPT), '--brief', str(self.brief_path),
                   '--delivery', str(self.delivery_path), '--root', str(self.artifact_root), '--output', str(output)]
        proc = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(output.read_text())['semantic_visual_status'], 'not_verified')
        (self.artifact_root / 'drawing.svg').write_bytes(b'tampered')
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)

    def test_variants_default_count_and_duplicate_ids(self):
        self.delivery['variants'].pop()
        self.assert_bad('variants count')
        self.delivery['variants'].append(copy.deepcopy(self.delivery['variants'][0]))
        self.assert_bad('duplicate variant id')

    def test_explicit_single_variant_allowed(self):
        self.brief['variant_count'] = 1
        self.brief_path.write_text(json.dumps(self.brief))
        self.delivery['brief_sha256'] = digest(self.brief_path.read_bytes())
        self.delivery['variants'] = self.delivery['variants'][:1]
        self.replace_archive(make_pdf(['V1']))
        self.assertEqual(self.check()['contract_status'], 'pass')

    def test_variants_sources_must_not_be_reused(self):
        self.delivery['variants'][1]['editable_artifact_ids'] = ['source']
        self.assert_bad('reuses another variant artifact')

    def test_variant_qa_kind_and_selected_id(self):
        self.delivery['variants'][0]['qa_artifact_id'] = 'ref'
        self.assert_bad('must have kind qa')
        self.delivery['variants'][0]['qa_artifact_id'] = 'qa'
        self.delivery['selected_variant_id'] = 'unknown'
        self.assert_bad('selected_variant_id')

    def test_archive_actual_pdf_parse_not_extension(self):
        self.replace_archive(b'not a PDF')
        self.assert_bad('lacks PDF magic')
        self.replace_archive(b'%PDF-1.4\nbroken')
        self.assert_bad('cannot be parsed')

    def test_archive_requires_numbered_pages(self):
        self.replace_archive(make_pdf(['V1', 'wrong', 'V3']))
        self.assert_bad('lacks extractable variant ID')

    def test_archive_pages_no_overlap_or_gaps(self):
        self.delivery['variants'][1]['pdf_pages'] = [1]
        self.assert_bad('assigned more than once')
        self.delivery['variants'][1]['pdf_pages'] = [4]
        self.assert_bad('out of range')
        self.delivery['variants'][1]['pdf_pages'] = [2]
        self.replace_archive(make_pdf(['V1', 'V2', 'V3', 'unassigned']))
        self.assert_bad('all be assigned exactly once')

    def test_completed_archive_required(self):
        self.delivery.pop('archive_pdf_artifact_id')
        self.assert_bad('archive_pdf_artifact_id')

    def test_pdf_variant_label_uses_token_boundaries(self):
        self.replace_archive(make_pdf(['V10', 'V2', 'V3']))
        self.assert_bad('lacks extractable variant ID')
        self.replace_archive(make_pdf(['Variant: V1', 'Variant: V2', 'Variant: V3']))
        result = self.check()
        self.assertEqual(result['contract_status'], 'pass', result['errors'])
        self.assertEqual(result['archive_pdf']['numbering_status'], 'pass')

    def test_distinct_artifact_ids_cannot_hide_identical_rendered_bytes(self):
        raw = (self.artifact_root / 'drawing.svg').read_bytes()
        (self.artifact_root / 'drawing2.svg').write_bytes(raw)
        next(a for a in self.delivery['artifacts'] if a['id'] == 'render2')['sha256'] = digest(raw)
        self.assert_bad('rendered SHA set identical')
