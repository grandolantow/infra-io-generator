import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/technical-architecture-diagrams/scripts'
sys.path.insert(0, str(SCRIPTS))
from route_request import route
from resolve_palette import resolve


class RoutingTests(unittest.TestCase):
    def test_model_layout_independent_of_presentation_target(self):
        for target in ('ppt', 'paper'):
            p = route('model architecture', intent='model', target=target)['parts'][0]['layout_preference']
            self.assertEqual(p['id'], 'vertical-backbone-side-detail')
            self.assertEqual(p['priority'], 'preferred_not_mandatory')
            self.assertEqual(p['side_detail'], 'when_explanatory')
            self.assertTrue(p['design_before_container'])
            self.assertTrue(p['deviation_requires_reason'])
            self.assertEqual(p['visual_review'], 'required')

    def test_report_layout_not_forced_vertical(self):
        p = route('memory mapping', intent='report', target='ppt')['parts'][0]['layout_preference']
        self.assertEqual(p['id'], 'task-appropriate')
        self.assertNotIn('side_detail', p)

    def test_mixed_layout_applies_per_part(self):
        parts = route('model and mechanism', intent='mixed', target='ppt')['parts']
        self.assertEqual([p['layout_preference']['id'] for p in parts],
                         ['vertical-backbone-side-detail', 'task-appropriate'])

    def test_ambiguous_layout_not_invented(self):
        self.assertEqual(route('make a slide')['parts'], [])

    def test_model_ppt_does_not_switch_palette(self):
        r = route('PPT里画模型完整主干和Attention/MoE层', target='ppt')
        self.assertEqual(r['intent'], 'model')
        self.assertEqual(r['parts'][0]['palette']['palette'], 'paper-clear')

    def test_paper_report(self):
        r = route('论文里解释PCP通信时序')
        self.assertEqual(r['intent'], 'report')
        self.assertEqual(r['parts'][0]['palette']['palette'], 'paper-vivid')

    def test_moe_dispatch(self):
        r = route('PPT画MoE all-to-all communication与token dispatch', target='ppt')
        self.assertEqual(r['intent'], 'report')
        self.assertEqual(r['parts'][0]['palette']['palette'], 'huawei-plain')

    def test_moe_block(self):
        self.assertEqual(route('画MoE block内部router/expert/combine结构')['intent'], 'model')

    def test_bare_attention_ambiguous(self):
        self.assertEqual(route('画Attention')['status'], 'needs_clarification')

    def test_attention_math_report(self):
        self.assertEqual(route('画Attention QKᵀ/softmax/V计算机制')['intent'], 'report')

    def test_attention_structure(self):
        self.assertEqual(route('画Transformer attention block的残差层结构')['intent'], 'model')

    def test_mixed(self):
        r = route('画K3整体架构，并展开PCP分片与通信', target='ppt')
        self.assertEqual(r['intent'], 'mixed')
        self.assertEqual([p['palette']['palette'] for p in r['parts']], ['paper-clear', 'huawei-plain'])
        self.assertTrue(r['shared_fact_contract'])

    def test_negation_needs_review(self):
        for text in ['不要模型架构，只画KV cache映射', '只画模型结构，不要性能图',
                     'not model architecture, only memory mapping']:
            with self.subTest(text=text):
                r = route(text)
                self.assertEqual(r['status'], 'needs_semantic_review')
                self.assertEqual(r['parts'], [])

    def test_explicit_semantic_review_result(self):
        self.assertEqual(route('不要模型架构，只画KV cache映射', intent='report')['intent'], 'report')

    def test_ppt_alone_not_intent(self):
        self.assertEqual(route('帮我画个PPT图', target='ppt')['parts'], [])

    def test_explicit_palette_wins(self):
        r = route('画模型主干', target='ppt', palette='paper-vivid')
        self.assertEqual(r['parts'][0]['palette']['palette'], 'paper-vivid')

    def test_custom_wins(self):
        r = route('通信图', target='ppt', palette='blue-neutral', custom={'accent': {'primary': '#9A1F2F'}})
        p = r['parts'][0]['palette']
        self.assertEqual(p['palette'], 'blue-neutral')
        self.assertEqual(p['tokens']['accent']['primary'], '#9A1F2F')

    def test_custom_base_is_report_default(self):
        p = route('时序图', target='ppt', palette='custom', custom={'accent': {'primary': '#9A1F2F'}})['parts'][0]['palette']
        self.assertEqual(p['palette'], 'huawei-plain')

    def test_report_word_not_intent(self):
        self.assertEqual(route('技术报告中画模型结构')['intent'], 'model')

    def test_model_word_not_intent(self):
        self.assertEqual(route('比较两个模型的吞吐/延迟曲线')['intent'], 'report')

    def test_mixed_explicit_palette(self):
        r = route('model and communication', intent='mixed', palette='blue-neutral')
        self.assertEqual({p['palette']['palette'] for p in r['parts']}, {'blue-neutral'})

    def test_legacy_resolver_unchanged(self):
        self.assertEqual(resolve('ppt')['palette'], 'paper-clear')

    def test_invalid_inputs(self):
        for kw in [{'request': ''}, {'request': '图', 'intent': 'x'}, {'request': '图', 'target': 'x'},
                   {'request': '图', 'palette': 'x'}, {'request': '图', 'palette': 'custom'}]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                route(**kw)

    def test_custom_contrast_uses_selected_branch(self):
        r = route('通信图', target='ppt', custom={'text': {'primary': '#676767'}})
        self.assertEqual(r['parts'][0]['palette']['tokens']['text']['primary'], '#676767')

    def test_cli_and_guides(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'route.json'
            subprocess.run([sys.executable, str(SCRIPTS / 'route_request.py'), '--request', 'PCP communication',
                            '--target', 'ppt', '--output', str(out)], check=True)
            r = json.loads(out.read_text())
            for part in r['parts']:
                self.assertTrue((SCRIPTS.parent / part['guide']).exists())
            self.assertEqual(r['status'], 'suggested')

class ReportPackageIntegrationTests(unittest.TestCase):
    def test_route_points_to_independent_report_package(self):
        r = route('memory mapping', intent='report')
        part = r['parts'][0]
        self.assertEqual(part['package'], 'technical-diagram-options')
        for relative in [part['guide'], part['overlay'], *part['runtime'].values()]:
            self.assertTrue((SCRIPTS.parent / relative).is_file(), relative)

    def test_report_selector_and_generator_are_invocable(self):
        part = route('memory mapping', intent='report')['parts'][0]
        report = ROOT / 'skills/technical-diagram-options'
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            subprocess.run([sys.executable, str(SCRIPTS.parent / part['runtime']['selector']),
                            str(report / 'examples/toy-mapping.task.json'), '--out', str(d / 'options.json')], check=True, capture_output=True)
            options = json.loads((d / 'options.json').read_text())
            self.assertGreaterEqual(len(options['options']), 2)
            generator = str(SCRIPTS.parent / part['runtime']['generator'])
            diagram = str(report / 'examples/toy-mapping.diagram.json')
            subprocess.run([sys.executable, generator, 'check', diagram], check=True, capture_output=True)
            subprocess.run([sys.executable, generator, 'render', diagram, '--out-dir', str(d / 'rendered')], check=True, capture_output=True)
            self.assertTrue(list((d / 'rendered').glob('*.svg')))
            self.assertTrue(list((d / 'rendered').glob('*.drawio')))

    def test_original_package_coverage_and_sanitization_manifest(self):
        import hashlib
        report = ROOT / 'skills/technical-diagram-options'
        m = json.loads((ROOT / 'reports/report-skill-files.json').read_text())
        self.assertEqual(len(m['files']), 25)
        for path in m['files']:
            self.assertTrue((report / path).is_file())
        for f in report.rglob('*'):
            if f.is_file() and f.suffix in ('.json', '.md', '.py'):
                text = f.read_text()
                self.assertNotIn('https://chatgpt.com/space/', text)
                self.assertNotIn('exact_table', text)

    def test_public_case_schema_and_archive_limit(self):
        report = ROOT / 'skills/technical-diagram-options'
        schema = json.loads((report / 'schemas/case.schema.json').read_text())
        cases = json.loads((report / 'references/cases.json').read_text())['cases']
        for case in cases:
            self.assertTrue(set(schema['required']).issubset(case))
            self.assertNotIn('visual_observations', case)
        sources = json.loads((report / 'references/sources.json').read_text())['sources']
        allowed = {'source_id','case_id','source_kind','title','url','qualified','paper_version','figure','page'}
        self.assertTrue(all(set(s).issubset(allowed) for s in sources))
        p = subprocess.run([sys.executable, str(report / 'scripts/check_package.py'), '--corpus-root', '.'], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('unavailable', p.stdout)
