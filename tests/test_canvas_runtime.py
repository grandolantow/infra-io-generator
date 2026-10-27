import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from xml.etree import ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'skills/technical-architecture-diagrams/scripts/drawio_runtime/export.mjs'


@unittest.skipUnless(os.environ.get('DIAGRAM_RUNTIME_TESTS') == '1', 'Run tools/check.py --runtime with Chromium')
class CanvasRuntimeTests(unittest.TestCase):
    def check_page(self, source, width, height, multipage=False):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            temp = Path(d)
            src = ROOT / source
            page_index = '0'
            if multipage:
                # The first page deliberately has a different aspect ratio.
                root = E.Element('mxfile')
                first = E.SubElement(root, 'diagram', name='landscape')
                E.SubElement(first, 'mxGraphModel', pageWidth='1600', pageHeight='900')
                page = E.parse(src).getroot().find('diagram')
                root.append(page)
                src = temp / 'two-pages.drawio'
                E.ElementTree(root).write(src, encoding='UTF-8')
                page_index = '1'
            args = ['node', str(RUNTIME), '--input', str(src), '--out', str(temp / 'result'),
                    '--graph-js', str(ROOT / 'third_party/drawio/app.min.js'),
                    '--chrome', os.environ['CHROME_BINARY'], '--page', page_index]
            subprocess.run(args, check=True, capture_output=True, text=True)
            svg = E.parse(temp / 'result.svg').getroot()
            self.assertEqual(svg.get('viewBox'), f'0 0 {width} {height}')
            with Image.open(temp / 'result.png') as im:
                self.assertEqual(im.size, (width, height))
            qa = json.loads((temp / 'result.runtime-qa.json').read_text())
            self.assertEqual(qa['javascript_errors'], [])
            self.assertGreater(qa['native_shape_metrics']['text'], 0)

    def test_portrait_selected_from_second_page(self):
        self.check_page('examples/minimax-m31/paper-clear/portrait.drawio', 680, 1660, True)

    def test_wide_detail_page(self):
        self.check_page('examples/minimax-m31/blue-neutral/detail.drawio', 1160, 460)

    def test_landscape_golden_page(self):
        self.check_page('skills/technical-architecture-diagrams/assets/golden-refined/attnres_refined.drawio', 1600, 900)
