import json
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as E

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_minimax_palette_keeps_native_structure(self):
        for name in ['portrait', 'detail']:
            a = E.parse(ROOT / 'examples/minimax-m31/paper-clear' / (name + '.drawio'))
            b = E.parse(ROOT / 'examples/minimax-m31/blue-neutral' / (name + '.drawio'))
            def strip_colors(tree):
                return re.sub(rb'#[0-9a-fA-F]{6}', b'#COLOR', E.tostring(tree.getroot()))
            self.assertEqual(strip_colors(a), strip_colors(b))

    def test_native_edges_have_existing_endpoints(self):
        for p in (ROOT / 'examples').rglob('*.drawio'):
            if p.name == 'LICENSE.drawio':
                continue  # Upstream license uses the same suffix as native diagrams.
            cells = E.parse(p).findall('.//mxCell')
            ids = {c.get('id') for c in cells}
            self.assertEqual(len(ids), len(cells), str(p))
            for c in cells:
                if c.get('edge') == '1':
                    self.assertIn(c.get('source'), ids)
                    self.assertIn(c.get('target'), ids)

    def test_no_machine_paths_in_maintained_sources(self):
        for base in ['tools', 'tests', 'skills']:
            for p in (ROOT / base).rglob('*'):
                if p.suffix not in ['.py', '.mjs', '.json', '.yaml', '.svg']:
                    continue
                text = p.read_text()
                for prefix in ['/work' + 'space/scratch/', '/ro' + 'ot/.codex/', '/Us' + 'ers/']:
                    self.assertNotIn(prefix, text, str(p))

    def test_skill_references_exist(self):
        skill = ROOT / 'skills/technical-architecture-diagrams'
        text = (skill / 'SKILL.md').read_text()
        for name in re.findall(r'`((?:references|assets|scripts)/[^` ]+)`', text):
            self.assertTrue((skill / name).exists(), name)

    def test_runtime_license_and_hash_match(self):
        import hashlib
        runtime = ROOT / 'third_party/drawio'
        pin = json.loads((runtime / 'graph-runtime.json').read_text())
        self.assertEqual(hashlib.sha256((runtime / 'app.min.js').read_bytes()).hexdigest(), pin['sha256'])
        self.assertTrue((runtime / 'LICENSE.drawio').exists())

    def test_visible_fact_ids_bind_to_shipped_figures(self):
        facts = json.loads((ROOT / 'examples/minimax-m31/facts.json').read_text())
        ids = {name: {c.get('id') for c in E.parse(ROOT / 'examples/minimax-m31/paper-clear' / (name + '.drawio')).findall('.//mxCell')}
               for name in ['portrait', 'detail']}
        for fact in facts['required_visual_facts']:
            for visible_id in fact['visible_ids']:
                figure, cell = visible_id.split('/', 1)
                self.assertIn(cell, ids[figure], fact['id'] + ': ' + visible_id)
