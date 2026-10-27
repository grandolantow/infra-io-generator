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
