"""Contract/regression tests; visual quality and editor behaviour are separate."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/technical-architecture-diagrams/scripts/svg_pipeline.py'
spec = importlib.util.spec_from_file_location('svg_pipeline_tested', SCRIPT)
pipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipe)


def fixture():
    return json.loads((ROOT / 'examples/svg-first/workflow.scene.json').read_text(encoding='utf-8'))


class SvgFirstTests(unittest.TestCase):
    def test_basic_build_and_semantic_hash(self):
        s = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            m = pipe.build(s, Path(tmp))
            self.assertEqual(m['semantic_sha256'], pipe.fingerprint(s['semantic']))
            for name in ['V1.svg', 'preview.html', 'diagram.drawio', 'semantic.json', 'layout.resolved.json']:
                self.assertTrue((Path(tmp) / name).is_file())
            self.assertEqual(m['validation']['visual'], 'not_run')
            self.assertEqual(m['validation']['GUI_drag'], 'not_run')

    def test_compile_does_not_mutate_input(self):
        s = fixture(); original = copy.deepcopy(s)
        pipe.compile_scene(s)
        self.assertEqual(s, original)

    def test_row_layout_and_ports(self):
        d = pipe.compile_scene(fixture()); v = d['views'][0]
        self.assertEqual([g['x'] for g in v['glyphs'][1:]], [50, 400, 750])
        self.assertEqual(v['paths'][0]['points'], [[330, 215], [400, 215]])

    def test_column_layout(self):
        s = fixture(); v = s['layout']['views'][0]
        v['arrangements'][0].update(axis='column', x=50, y=100, gap=20)
        v['canvas']['height'] = 520
        for p in v['paths']:
            p.update(source_port='bottom', target_port='top')
        d = pipe.compile_scene(s)
        self.assertEqual(d['views'][0]['paths'][0]['points'], [[190, 200], [190, 220]])
        pipe.validate(d)

    def test_ports_follow_moved_layout(self):
        s = fixture(); s['layout']['views'][0]['arrangements'][0]['y'] += 25
        p = pipe.compile_scene(s)['views'][0]['paths'][0]
        self.assertEqual(p['points'], [[330, 240], [400, 240]])

    def test_legacy_split_preserves_semantics_and_geometry(self):
        d = pipe.compile_scene(fixture())
        migrated = pipe.split_legacy(d)
        roundtrip = pipe.compile_scene(migrated)
        self.assertEqual(roundtrip['semantic'], d['semantic'])
        self.assertEqual(roundtrip['views'], d['views'])

    def test_unknown_semantic_node(self):
        s = fixture(); s['layout']['views'][0]['glyphs'][1]['semantic_ref'] = 'missing'
        with self.assertRaises(ValueError): pipe.compile_scene(s)

    def test_wrong_edge_relation_endpoints(self):
        d = pipe.compile_scene(fixture()); d['semantic']['edges'][0]['target'] = 'workload'
        with self.assertRaises(ValueError): pipe.validate(d)

    def test_canvas_overflow(self):
        s = fixture(); s['layout']['views'][0]['canvas']['width'] = 900
        with self.assertRaises(ValueError): pipe.validate(pipe.compile_scene(s))

    def test_nonfinite_or_zero_geometry(self):
        for value in [float('nan'), 0, -1, True]:
            s = fixture(); s['layout']['views'][0]['glyphs'][1]['w'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                pipe.validate(pipe.compile_scene(s))

    def test_duplicate_glyph(self):
        s = fixture(); s['layout']['views'][0]['glyphs'].append(copy.deepcopy(s['layout']['views'][0]['glyphs'][0]))
        with self.assertRaises(ValueError): pipe.compile_scene(s)

    def test_marker_id_collision(self):
        s = fixture(); g = s['layout']['views'][0]['glyphs'][0]; g['id'] = 'arrow-to-shape'
        with self.assertRaises(ValueError): pipe.validate(pipe.compile_scene(s))

    def test_detached_route_rejected(self):
        d = pipe.compile_scene(fixture()); d['views'][0]['paths'][0]['points'][0] = [340, 215]
        with self.assertRaises(ValueError): pipe.validate(d)

    def test_two_view_svg_ids_are_unique(self):
        s = fixture(); v = copy.deepcopy(s['layout']['views'][0]); v['id'] = 'V2'
        s['layout']['views'].append(v)
        d = pipe.compile_scene(s); ids = []
        for view in d['views']:
            tree = pipe.svg_tree(view, d)
            ids.extend(e.get('id') for e in tree.iter() if e.get('id'))
        self.assertEqual(len(ids), len(set(ids)))

    def test_text_is_text_not_raster(self):
        d = pipe.compile_scene(fixture()); tree = pipe.svg_tree(d['views'][0], d)
        self.assertGreater(len(list(tree.iter('text'))), 0)
        self.assertEqual(list(tree.iter('image')), [])

    def test_drawio_native_objects_and_edges(self):
        d = pipe.compile_scene(fixture()); tree = pipe.drawio_tree(d)
        edge = next(e for e in tree.iter('mxCell') if e.get('id') == 'to-shape')
        self.assertEqual(edge.get('source'), 'input')
        self.assertEqual(edge.get('target'), 'derive')
        self.assertEqual(edge.get('semanticRef'), 'derive')
        self.assertFalse(any(e.tag == 'image' for e in tree.iter()))

    def test_bold_text_in_both_exports(self):
        d = pipe.compile_scene(fixture())
        svg = pipe.svg_tree(d['views'][0], d)
        text = next(e for e in svg.iter('text') if e.get('font-weight') == '600')
        self.assertIsNotNone(text)
        cell = next(e for e in pipe.drawio_tree(d).iter('mxCell') if e.get('id') == 'heading')
        self.assertIn('fontStyle=1;', cell.get('style'))

    def test_style_only_edit_keeps_semantics(self):
        s = fixture(); before = pipe.fingerprint(s['semantic'])
        s['theme']['roles']['focus']['stroke'] = '#334455'
        self.assertEqual(pipe.fingerprint(pipe.compile_scene(s)['semantic']), before)

    def test_unsafe_external_color_rejected(self):
        s = fixture(); s['theme']['edge']['stroke'] = 'url(https://example.invalid/x.svg)'
        with self.assertRaises(ValueError): pipe.validate(pipe.compile_scene(s))

    def test_script_payload_escaped(self):
        s = fixture(); s['semantic']['facts'][0]['statement'] = '</script><script>alert(1)</script>'
        d = pipe.compile_scene(s)
        text = pipe.html_viewer(d, {'V1': '<svg></svg>'})
        self.assertNotIn('</script><script>alert(1)', text)
        self.assertIn('\\u003c/script', text)

    def test_no_recursive_template_replacement(self):
        d = pipe.compile_scene(fixture())
        page = pipe.html_viewer(d, {'V1': '<svg><text>{{DATA}}</text></svg>'})
        self.assertIn('<text>{{DATA}}</text>', page)

    def test_rebuild_deterministic(self):
        s = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            a = pipe.build(s, Path(tmp)); b = pipe.build(s, Path(tmp))
            self.assertEqual(a, b)

    def test_modified_svg_and_drawio_not_overwritten(self):
        for name in ['V1.svg', 'diagram.drawio']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp); pipe.build(fixture(), p)
                (p / name).write_text('USER EDIT', encoding='utf-8')
                with self.assertRaises(ValueError): pipe.build(fixture(), p)
                self.assertEqual((p / name).read_text(), 'USER EDIT')

    def test_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); pipe.build(fixture(), p)
            (p / 'V1.svg').write_text('USER EDIT')
            pipe.build(fixture(), p, overwrite_edits=True)
            self.assertTrue((p / 'V1.svg').read_text().startswith('<svg'))

    def test_drawio_optional_and_stale_output_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); pipe.build(fixture(), p)
            pipe.build(fixture(), p, with_drawio=False)
            self.assertFalse((p / 'diagram.drawio').exists())

    def test_locked_layout_not_rearranged(self):
        s = fixture(); s['layout']['views'][0]['glyphs'][1]['locked'] = True
        with self.assertRaises(ValueError): pipe.compile_scene(s)

    def test_missing_profile_rejected(self):
        s = fixture(); s.pop('language_profile')
        with self.assertRaises(ValueError): pipe.compile_scene(s)

    def test_shared_language_check_still_runs(self):
        s = fixture(); s['semantic']['nodes'][0]['label'] = '图内中文标签'
        with self.assertRaises(ValueError): pipe.validate(pipe.compile_scene(s))

    def test_missing_fact_provenance_rejected(self):
        s = fixture(); s['semantic']['facts'][0]['provenance'] = ''
        with self.assertRaises(ValueError): pipe.validate(pipe.compile_scene(s))

    def test_mixed_route_encoding_rejected(self):
        s = fixture(); s['layout']['views'][0]['paths'][0]['points'] = [[0,0],[1,1]]
        with self.assertRaises(ValueError): pipe.compile_scene(s)

    def test_scope_and_qas_do_not_claim_visual_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = pipe.build(fixture(), Path(tmp))
            self.assertEqual(m['validation']['source_fact_review'], 'not_run')
            self.assertEqual(m['validation']['drawio_editor'], 'not_run')

    def test_shared_palette_explicit_roles_and_overrides(self):
        s = fixture(); s['theme'] = {'palette': 'paper-clear'}
        s['layout']['views'][0]['glyphs'][1]['style_role'] = 'compute'
        d = pipe.compile_scene(s)
        self.assertEqual(d['views'][0]['glyphs'][1]['style']['fill'], '#DDECF7')
        s['theme']['base'] = {'text_color': '#111111'}
        self.assertEqual(pipe.compile_scene(s)['views'][0]['glyphs'][1]['style']['text_color'], '#111111')

    def test_auto_palette_requires_semantic_routing_first(self):
        s = fixture(); s['theme']['palette'] = 'auto'
        with self.assertRaises(ValueError): pipe.compile_scene(s)


    def test_namespace_handles_delimiter_in_view_id(self):
        s = fixture(); a = s['layout']['views'][0]; a['id'] = 'A'
        a['glyphs'][0]['id'] = 'B--heading'
        b = copy.deepcopy(a); b['id'] = 'A--B'; b['glyphs'][0]['id'] = 'heading'
        s['layout']['views'].append(b)
        d = pipe.compile_scene(s); ids = []
        for v in d['views']:
            ids.extend(e.get('id') for e in pipe.svg_tree(v, d).iter() if e.get('id'))
        self.assertEqual(len(ids), len(set(ids)))

    def test_dropping_edited_export_still_requires_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); pipe.build(fixture(), p)
            (p / 'diagram.drawio').write_text('USER EDIT')
            with self.assertRaises(ValueError): pipe.build(fixture(), p, with_drawio=False)
            self.assertEqual((p / 'diagram.drawio').read_text(), 'USER EDIT')



class RoutingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = str(SCRIPT.parent)
        sys.path.insert(0, directory)
        spec = importlib.util.spec_from_file_location('svg_first_route', SCRIPT.parent / 'route_request.py')
        cls.router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.router)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPT.parent))

    def test_default_renderer_preserves_model_palette(self):
        r = self.router.route('model architecture', intent='model', target='ppt')
        self.assertEqual(r['rendering']['primary'], 'svg-first')
        self.assertEqual(r['parts'][0]['palette']['palette'], 'paper-clear')
        self.assertEqual(r['parts'][0]['layout_preference']['id'], 'vertical-backbone-side-detail')

    def test_report_preserves_selector_and_plain_palette(self):
        r = self.router.route('dataflow', intent='report', target='ppt')
        self.assertEqual(r['parts'][0]['palette']['palette'], 'huawei-plain')
        self.assertTrue(r['parts'][0]['runtime']['selector'].endswith('select_options.py'))
        self.assertEqual(r['rendering']['entrypoint'], 'scripts/svg_pipeline.py')

    def test_legacy_renderer_is_explicit(self):
        r = self.router.route('dataflow', intent='report', renderer='drawio-legacy')
        self.assertEqual(r['rendering']['primary'], 'drawio-legacy')
        self.assertIsNone(r['rendering']['entrypoint'])

    def test_unimplemented_canvas_is_rejected(self):
        with self.assertRaises(ValueError):
            self.router.route('dataflow', renderer='canvas')

    def test_ambiguous_intent_stays_ambiguous(self):
        r = self.router.route('Attention')
        self.assertEqual(r['status'], 'needs_clarification')
        self.assertEqual(r['parts'], [])


if __name__ == '__main__':
    unittest.main()
