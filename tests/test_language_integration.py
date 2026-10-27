import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'skills/technical-diagram-options'
MODEL = ROOT / 'skills/technical-architecture-diagrams'

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

tool = load_module('language_diagram_tool', REPORT / 'scripts/diagram_tool.py')
checker = load_module('language_shared_checker', MODEL / 'scripts/check_language.py')

class LanguageIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((REPORT / 'examples/toy-mapping.language.diagram.json').read_text())

    def test_direct_report_generator_consumes_shared_profile(self):
        result = tool.check(self.doc)
        self.assertTrue(result['valid'])
        self.assertEqual(result['language_qa']['status'], 'needs_review')
        bad = copy.deepcopy(self.doc)
        bad['views'][0]['glyphs'][0]['text_role'] = 'node_label'
        bad['views'][0]['glyphs'][0]['label_lines'] = ['错误中文功能标签']
        self.assertFalse(tool.check(bad)['valid'])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                tool.render(bad, d)

    def test_native_role_preservation_and_bound_qa(self):
        with tempfile.TemporaryDirectory() as d:
            tool.render(self.doc, d)
            root = Path(d)
            source = root / 'toy_mapping_language.source.json'
            qa = json.loads((root / 'language-qa.json').read_text())
            self.assertEqual(qa['input_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            tree = E.parse(root / 'toy_mapping_language.drawio')
            self.assertEqual(tree.getroot().get('language_profile'), self.doc['language_profile'])
            for c in tree.findall('.//mxCell'):
                if c.get('value'):
                    self.assertTrue(c.get('text_role'))
            result = checker.check_document(tree.getroot(), format='model')
            self.assertEqual(result['contract_status'], 'pass')
            self.assertEqual(result['semantic_review'], 'not_run')
            svg = E.parse(root / 'mapping.svg')
            ns = {'s':'http://www.w3.org/2000/svg'}
            self.assertTrue(svg.findall('.//s:g[@data-text-role]', ns))

    def test_legacy_render_does_not_claim_language_pass(self):
        legacy = json.loads((REPORT / 'examples/toy-mapping.diagram.json').read_text())
        self.assertEqual(tool.check(legacy)['language_qa']['status'], 'not_run')

    def test_both_entries_reference_shared_policy(self):
        for package in [REPORT, MODEL]:
            text = (package / 'SKILL.md').read_text()
            self.assertIn('text-language.md', text)
            self.assertIn('diagram-en-prose-zh', text)

    def test_explicit_invalid_profile_is_not_legacy(self):
        for value in ['', None, 0, 'block-en-surrounding-zh']:
            with self.subTest(value=value):
                doc = copy.deepcopy(self.doc)
                doc['language_profile'] = value
                self.assertFalse(tool.check(doc)['valid'])
                self.assertEqual(tool.check(doc)['language_qa']['status'], 'fail')

    def test_schema_roles_match_shared_profile(self):
        config = json.loads((MODEL / 'references/language-profile.json').read_text())
        schema = json.loads((REPORT / 'schemas/diagram.schema.json').read_text())
        self.assertEqual(schema['properties']['language_profile']['const'], config['id'])
        v = schema['properties']['views']['items']['properties']
        for value in [v['title_text_role'], v['scope_text_role'], v['glyphs']['items']['properties']['text_role'], v['paths']['items']['properties']['text_role']]:
            self.assertEqual(set(value['enum']), set(config['roles']))

    def test_language_and_structural_reports_bind_same_source(self):
        with tempfile.TemporaryDirectory() as d:
            tool.render(self.doc, d)
            root = Path(d)
            qa = json.loads((root / 'language-qa.json').read_text())
            nested = json.loads((root / 'structural-qa.json').read_text())['language_qa']
            self.assertEqual(qa, nested)
            svg = E.parse(root / 'mapping.svg')
            self.assertEqual(svg.find('{http://www.w3.org/2000/svg}title').get('data-text-role'), 'diagram_title')
            self.assertEqual(svg.find('{http://www.w3.org/2000/svg}desc').get('data-text-role'), 'prose')
