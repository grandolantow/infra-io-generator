import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/technical-architecture-diagrams/scripts/check_language.py'
spec = importlib.util.spec_from_file_location('diagram_language_checker', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def doc():
    return {'language_profile': checker.PROFILE, 'views': [{'id': 'v', 'title': 'Cache Mapping', 'title_text_role': 'diagram_title',
        'scope': '只表示逻辑映射', 'scope_text_role': 'prose', 'glyphs': [
        {'id': 'n', 'label_lines': ['KV Cache'], 'text_role': 'node_label'},
        {'id': 'large_container', 'label': 'Cache Management', 'text_role': 'section_title',
         'shape': 'rect', 'w': 1000, 'h': 1000},
        {'id': 'math', 'label': 'QKᵀ / √d', 'text_role': 'formula'}],
        'paths': [{'id': 'edge', 'label': 'Transfer KV on demand', 'text_role': 'edge_annotation'}]}],
        'surrounding_texts': [{'id': 'title', 'text': 'Cache Transfer', 'text_role': 'diagram_title'},
                              {'id': 'source', 'text': '来源：论文 Figure 2', 'text_role': 'source_citation'},
                              {'id': 'limit', 'text': '仅表示逻辑关系', 'text_role': 'prose'},
                              {'id': 'legend', 'text': 'Dashed: control', 'text_role': 'legend'}]}


class LanguageTests(unittest.TestCase):
    def test_positive_roles_still_need_semantic_review(self):
        r = checker.check_document(doc())
        self.assertEqual(r['contract_status'], 'pass')
        self.assertEqual(r['status'], 'needs_review')
        self.assertEqual(r['semantic_review'], 'not_run')
        self.assertEqual(r['coverage']['surrounding_texts'], 6)
        self.assertEqual(r['coverage']['rendered_coverage'], 'not_verified')
        self.assertEqual(r['warnings'], [])

    def test_chinese_functional_node_fails_without_translation(self):
        d = doc(); d['views'][0]['glyphs'][0]['label_lines'] = ['缓存']
        before = copy.deepcopy(d)
        r = checker.check_document(d)
        self.assertEqual(r['status'], 'fail')
        self.assertTrue(any('Han' in x for x in r['errors']))
        self.assertEqual(before, d)

    def test_missing_role_fails_even_if_text_looks_english(self):
        d = doc(); del d['views'][0]['glyphs'][0]['text_role']
        r = checker.check_document(d)
        self.assertEqual(r['coverage']['unclassified_texts'], 1)
        self.assertEqual(r['contract_status'], 'fail')

    def test_container_geometry_never_makes_context_english(self):
        d = doc(); g = d['views'][0]['glyphs'][1]
        g['text_role'] = 'prose'; g['label'] = '模型内部按需保存 KV'
        self.assertEqual(checker.check_document(d)['contract_status'], 'pass')
        g['label'] = 'This is an external explanation'
        r = checker.check_document(d)
        self.assertEqual(r['contract_status'], 'pass')
        self.assertTrue(any('prose' in x for x in r['warnings']))

    def test_symbols_and_model_names_are_not_translated(self):
        d = doc()
        d['surrounding_texts'] = [{'id': role, 'text': text, 'text_role': role}
                                for role, text in [('technical_term', 'AllGather'),
                                                   ('model_name', 'DeepSeek-V2'),
                                                   ('variable', 'x_t'), ('formula', 'x < y')]]
        self.assertEqual(checker.check_document(d)['warnings'], [])

    def test_semantic_metadata_is_not_visible_text(self):
        d = doc(); d['semantic'] = {'facts': [{'statement': 'English fact, not visible output'}]}
        self.assertEqual(checker.check_document(d)['warnings'], [])

    def test_empty_labels_do_not_require_role(self):
        d = doc(); d['views'][0]['glyphs'].append({'id': 'empty', 'label': '  '})
        r = checker.check_document(d)
        self.assertEqual(r['contract_status'], 'pass')
        self.assertEqual(r['coverage']['empty_texts'], 1)

    def test_invalid_role_and_profile(self):
        d = doc(); d['surrounding_texts'][0]['text_role'] = 'whatever'
        self.assertEqual(checker.check_document(d)['contract_status'], 'fail')
        self.assertEqual(checker.check_document(doc(), profile='unknown')['contract_status'], 'fail')
        self.assertEqual(checker.check_document(doc(), format='unknown')['contract_status'], 'fail')

    def test_declared_profile_mismatch(self):
        d = doc(); d['language_profile'] = 'another'
        self.assertTrue(any('does not match' in x for x in checker.check_document(d)['errors']))

    def test_model_xml_with_html(self):
        xml = '<mxfile language_profile="diagram-en-prose-zh"><diagram><mxGraphModel><root><mxCell id="n" value="&lt;b&gt;MoE&lt;/b&gt;" style="html=1;" text_role="node_label"/><mxCell id="caption" value="专家路由说明" text_role="prose"/></root></mxGraphModel></diagram></mxfile>'
        r = checker.check_document(xml, format='model')
        self.assertEqual(r['contract_status'], 'pass')
        self.assertEqual(r['coverage']['checked_texts'], 2)

    def test_wrapper_chinese_functional_label_fails(self):
        for tag in ('object', 'UserObject'):
            xml = f'<mxfile><{tag} id="n" label="缓存" text_role="node_label"><mxCell value="" vertex="1"/></{tag}></mxfile>'
            r = checker.check_document(xml, 'model')
            self.assertEqual(r['status'], 'fail')
            self.assertEqual(r['coverage']['wrapper_texts'], 1)
            self.assertTrue(any('Han' in e for e in r['errors']))

    def test_wrapper_english_label_and_explicit_role_fallback(self):
        for tag in ('object', 'UserObject'):
            xml = f'<mxfile><{tag} id="n" label="KV Cache"><mxCell value="" text_role="node_label" vertex="1"/></{tag}></mxfile>'
            r = checker.check_document(xml, 'model')
            self.assertEqual(r['contract_status'], 'pass')
            self.assertEqual(r['coverage']['source_texts'], 1)
            self.assertEqual(r['coverage']['wrapper_texts'], 1)
            self.assertEqual(r['coverage']['empty_texts'], 1)
            self.assertEqual(checker.check_document(xml.replace(' text_role="node_label"', ''), 'model')['status'], 'fail')
            conflict = xml.replace('label="KV Cache"', 'label="KV Cache" text_role="prose"')
            self.assertTrue(any('conflict' in e for e in checker.check_document(conflict, 'model')['errors']))

    def test_model_legacy_and_compressed_are_not_certified(self):
        for xml in ['<mxfile><mxCell id="n" value="MLA"/></mxfile>',
                    '<mxfile><diagram>compressed-data</diagram></mxfile>']:
            self.assertEqual(checker.check_document(xml, 'model')['status'], 'fail')

    def test_xml_entities_not_loaded(self):
        xml = '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///not-readable">]><mxfile><mxCell value="&e;" text_role="node_label"/></mxfile>'
        self.assertEqual(checker.check_document(xml, 'model')['status'], 'fail')

    def test_malformed_fields_are_contract_errors(self):
        for d in [[], {'views': 'no'}, {'views': [{'glyphs': [3]}]},
                  {'views': [{'glyphs': [{'label_lines': [3]}]}]}]:
            self.assertEqual(checker.check_document(d)['contract_status'], 'fail')

    def test_cli_report_and_model_hash_exact_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for fmt, text in [('report', json.dumps(doc(), ensure_ascii=False)),
                              ('model', '<mxfile><mxCell value="MLA" text_role="node_label"/></mxfile>')]:
                source = p / (fmt + '.txt'); source.write_text(text)
                out = p / fmt / 'qa.json'
                result = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source),
                                         '--format', fmt, '--profile', checker.PROFILE,
                                         '--output', str(out)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                qa = json.loads(out.read_text())
                self.assertEqual(qa['input_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
                self.assertEqual(qa['status'], 'needs_review')

    def test_view_title_and_scope_have_explicit_roles(self):
        d = doc(); del d['views'][0]['title_text_role']
        self.assertEqual(checker.check_document(d)['contract_status'], 'fail')
        d = doc(); d['views'][0]['scope'] = 'English scope note'
        self.assertTrue(any('/scope' in x for x in checker.check_document(d)['warnings']))
        d = doc(); del d['views'][0]['title']
        self.assertTrue(any('view title' in x for x in checker.check_document(d)['errors']))

    def test_edge_annotation_is_english_without_length_guessing(self):
        d = doc()
        self.assertEqual(checker.check_document(d)['contract_status'], 'pass')
        d['views'][0]['paths'][0]['label'] = '传输 KV'
        self.assertEqual(checker.check_document(d)['contract_status'], 'fail')
        d['views'][0]['paths'][0]['text_role'] = 'prose'
        self.assertEqual(checker.check_document(d)['contract_status'], 'pass')

    def test_plain_labels_are_not_silently_html_decoded(self):
        d = doc(); d['views'][0]['glyphs'][0]['label_lines'] = ['<span title="缓存">KV</span>']
        self.assertEqual(checker.check_document(d)['contract_status'], 'fail')
        xml = '<mxfile><mxCell value="&lt;span title=&quot;缓存&quot;&gt;KV&lt;/span&gt;" style="html=0;" text_role="node_label"/></mxfile>'
        self.assertEqual(checker.check_document(xml, 'model')['contract_status'], 'fail')
        xml = xml.replace('html=0;', 'html=1;')
        self.assertEqual(checker.check_document(xml, 'model')['contract_status'], 'pass')

    def test_cli_failure_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'legacy.drawio'; source.write_text('<mxfile><mxCell value="MLA"/></mxfile>')
            result = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source), '--format', 'model'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['status'], 'fail')
