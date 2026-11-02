"""Package-level compatibility tests; fixtures need no PowerPoint dependency."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'skills/technical-architecture-diagrams/scripts/figgenie_export.py'
spec = importlib.util.spec_from_file_location('figgenie_export_compat', PATH)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
INVARIANT = 'all_package_parts_unchanged_except_selected_effectRef_indices'


def rels(*entries):
    return ('<Relationships xmlns="' + PKG + '">' + ''.join(
        f'<Relationship Id="rId{i}" Type="{R}/{kind}" Target="{target}"/>'
        for i, (kind, target) in enumerate(entries, 1)) + '</Relationships>').encode()


def shape(name, idx=2, *, connector=False, explicit='', quote='"'):
    tag = 'cxnSp' if connector else 'sp'
    nv = ('<p:nvCxnSpPr><p:cNvPr id="12" name="wire"/><p:cNvCxnSpPr>'
          '<a:stCxn id="7" idx="1"/><a:endCxn id="9" idx="3"/>'
          '</p:cNvCxnSpPr><p:nvPr/></p:nvCxnSpPr>' if connector else
          f'<p:nvSpPr><p:cNvPr id="7" name="{name}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>')
    return (f'<p:{tag}>' + nv + '<p:spPr><a:xfrm rot="120000">'
            '<a:off x="12345" y="67890"/><a:ext cx="89012" cy="34567"/>'
            '</a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>' + explicit +
            '</p:spPr><p:style><a:lnRef idx="1"><a:schemeClr val="accent1"/></a:lnRef>'
            f'<a:effectRef idx={quote}{idx}{quote}><a:schemeClr val="accent2"/></a:effectRef>'
            '</p:style><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r>'
            f'<a:t>{name}</a:t></a:r></a:p></p:txBody></p:{tag}>')


def slide(content):
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}">'
            '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name="root"/>'
            '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>' + content +
            '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>').encode()


def theme(styles):
    return (f'<a:theme xmlns:a="{A}" name="fixture"><a:themeElements>'
            '<a:clrScheme name="colors"/><a:fontScheme name="fonts"/>'
            '<a:fmtScheme name="effects"><a:fillStyleLst/><a:lnStyleLst/>'
            '<a:effectStyleLst>' + ''.join('<a:effectStyle>' + effects + '</a:effectStyle>'
                                         for effects in styles) +
            '</a:effectStyleLst><a:bgFillStyleLst/></a:fmtScheme>'
            '</a:themeElements></a:theme>').encode()


SHADOW = '<a:effectLst><a:outerShdw blurRad="40000"><a:srgbClr val="000000"/></a:outerShdw></a:effectLst>'
GLOW = '<a:effectLst><a:glow rad="20000"><a:srgbClr val="FFFFFF"/></a:glow></a:effectLst>'


class GeneratedPptxCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.svg = self.base / 'source.svg'
        self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200"><rect id="node" width="20" height="20"/></svg>')
        self.generated = self.base / 'generated.pptx'
        self.output = self.base / 'normalized.pptx'

    def package(self, slides=None, themes=None):
        slides = slides or [slide(shape('node'))]
        themes = themes or [theme(['<a:effectLst/>', SHADOW, GLOW]) for _ in slides]
        parts = {
            '[Content_Types].xml': b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
            '_rels/.rels': rels(('officeDocument', 'ppt/presentation.xml')),
            'ppt/presentation.xml': (f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst>' + ''.join(
                f'<p:sldId id="{256+i}" r:id="rId{i+1}"/>' for i in range(len(slides))) +
                '</p:sldIdLst></p:presentation>').encode(),
            'ppt/_rels/presentation.xml.rels': rels(*[('slide', f'slides/slide{i+1}.xml') for i in range(len(slides))]),
            'ppt/media/untouched.bin': b'\x00original opaque media\xff',
            'docProps/custom.xml': b'<custom>must remain byte-identical</custom>',
        }
        for i, (slide_data, theme_data) in enumerate(zip(slides, themes), 1):
            parts.update({
                f'ppt/slides/slide{i}.xml': slide_data,
                f'ppt/slides/_rels/slide{i}.xml.rels': rels(('slideLayout', f'../slideLayouts/slideLayout{i}.xml')),
                f'ppt/slideLayouts/slideLayout{i}.xml': f'<p:sldLayout xmlns:p="{P}"/>'.encode(),
                f'ppt/slideLayouts/_rels/slideLayout{i}.xml.rels': rels(('slideMaster', f'../slideMasters/slideMaster{i}.xml')),
                f'ppt/slideMasters/slideMaster{i}.xml': f'<p:sldMaster xmlns:p="{P}"/>'.encode(),
                f'ppt/slideMasters/_rels/slideMaster{i}.xml.rels': rels(('theme', f'../theme/theme{i}.xml')),
                f'ppt/theme/theme{i}.xml': theme_data,
            })
        return parts

    def write_package(self, parts):
        with zipfile.ZipFile(self.generated, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in parts.items():
                archive.writestr(name, data)

    def normalize(self, parts):
        self.write_package(parts)
        return exporter.normalize_generated_pptx(self.svg, self.generated, self.output)

    def assert_parts(self, expected):
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(set(archive.namelist()), set(expected))
            for name, data in expected.items():
                with self.subTest(part=name):
                    self.assertEqual(archive.read(name), data)

    def test_only_shadow_references_change_and_every_other_byte_is_preserved(self):
        group = '<p:grpSp><p:nvGrpSpPr><p:cNvPr id="40" name="semantic-group"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
        content = (group + shape('Chinese 文本 &amp; labels', quote="'") + shape('connector', connector=True) +
                   '</p:grpSp>' + shape('no-effect', idx=0) + shape('empty-effect', idx=1) + shape('glow', idx=3))
        parts = self.package([slide(content)])
        before = parts['ppt/slides/slide1.xml']
        result = self.normalize(parts)
        expected = dict(parts)
        expected['ppt/slides/slide1.xml'] = before.replace(b"<a:effectRef idx='2'", b"<a:effectRef idx='0'").replace(
            b'<a:effectRef idx="2"', b'<a:effectRef idx="0"')
        self.assert_parts(expected)
        self.assertEqual(result['status'], 'applied')
        self.assertEqual(result['changed_references'], 2)
        self.assertEqual(len(result['changes']), 2)
        self.assertEqual(result['invariant'], INVARIANT)
        self.assertEqual(result['before_sha256'], hashlib.sha256(self.generated.read_bytes()).hexdigest())
        self.assertEqual(result['after_sha256'], hashlib.sha256(self.output.read_bytes()).hexdigest())
        with zipfile.ZipFile(self.generated) as archive:
            self.assertEqual(archive.read('ppt/slides/slide1.xml'), before)

    def test_theme_is_resolved_per_slide_instead_of_by_global_style_index(self):
        parts = self.package([slide(shape('shadow')), slide(shape('glow'))],
                             [theme(['<a:effectLst/>', SHADOW]), theme(['<a:effectLst/>', GLOW])])
        result = self.normalize(parts)
        expected = dict(parts)
        expected['ppt/slides/slide1.xml'] = parts['ppt/slides/slide1.xml'].replace(b'idx="2"><a:schemeClr', b'idx="0"><a:schemeClr')
        self.assert_parts(expected)
        self.assertEqual(result['changed_references'], 1)

    def test_explicit_object_effects_and_non_shape_references_are_untouched(self):
        content = (shape('explicit-list', explicit=SHADOW) +
                   shape('explicit-dag', explicit='<a:effectDag><a:outerShdw/></a:effectDag>') +
                   '<p:graphicFrame><p:style><a:effectRef idx="2"/></p:style></p:graphicFrame>' +
                   '<p:grpSp><p:style><a:effectRef idx="2"/></p:style></p:grpSp>' + shape('zero', idx=0))
        parts = self.package([slide(content)])
        result = self.normalize(parts)
        self.assert_parts(parts)
        self.assertEqual(result['status'], 'not_needed')
        self.assertEqual(result['changed_references'], 0)
        self.assertEqual(result['changes'], [])

    def test_no_shadow_is_not_needed_and_all_parts_are_unchanged(self):
        parts = self.package([slide(shape('glow', idx=2) + shape('empty', idx=1))],
                             [theme(['<a:effectLst/>', GLOW])])
        result = self.normalize(parts)
        self.assert_parts(parts)
        self.assertEqual(result['status'], 'not_needed')
        self.assertEqual(result['changed_references'], 0)
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['invariant'], INVARIANT)

    def test_corrupt_zip_is_rejected_without_creating_output(self):
        original = b'not a ZIP presentation'
        self.generated.write_bytes(original)
        with self.assertRaises(zipfile.BadZipFile):
            exporter.normalize_generated_pptx(self.svg, self.generated, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.generated.read_bytes(), original)

    def test_each_shadow_kind_is_normalized(self):
        for tag in ('outerShdw', 'innerShdw', 'prstShdw'):
            with self.subTest(tag=tag):
                self.output.unlink(missing_ok=True)
                parts = self.package(themes=[theme(['<a:effectLst/>', f'<a:effectLst><a:{tag}/></a:effectLst>'])])
                self.assertEqual(self.normalize(parts)['changed_references'], 1)

    def test_existing_output_is_never_overwritten(self):
        self.write_package(self.package())
        original = b'user edited presentation'
        self.output.write_bytes(original)
        with self.assertRaises(ValueError):
            exporter.normalize_generated_pptx(self.svg, self.generated, self.output)
        self.assertEqual(self.output.read_bytes(), original)

    def test_source_effects_are_rejected_without_creating_output(self):
        for extra in ('<filter id="f"/>', '<rect filter="url(#f)"/>', '<rect style="filter:drop-shadow(1px 2px black)"/>',
                      '<rect style="text-shadow:1px 1px black"/>', '<rect style="box-shadow:1px 1px black"/>',
                      '<rect text-shadow="1px 1px black"/>', '<rect box-shadow="1px 1px black"/>',
                      '<style>rect {filter:url(#f)}</style>'):
            with self.subTest(extra=extra):
                self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200">' + extra + '</svg>')
                original = self.svg.read_bytes()
                self.write_package(self.package())
                with self.assertRaises(ValueError):
                    exporter.normalize_generated_pptx(self.svg, self.generated, self.output)
                self.assertFalse(self.output.exists())
                self.assertEqual(self.svg.read_bytes(), original)

    def test_ambiguous_or_invalid_packages_fail_without_creating_output(self):
        cases = {}
        parts = self.package()
        del parts['ppt/slideLayouts/_rels/slideLayout1.xml.rels']
        cases['missing relationship'] = parts
        parts = self.package()
        parts['ppt/slideMasters/_rels/slideMaster1.xml.rels'] = rels(('theme', '../theme/missing.xml'))
        cases['missing theme target'] = parts
        parts = self.package()
        parts['ppt/slides/_rels/slide1.xml.rels'] = rels(('slideLayout', '../slideLayouts/slideLayout1.xml'), ('themeOverride', '../theme/themeOverride1.xml'))
        parts['ppt/theme/themeOverride1.xml'] = f'<a:themeOverride xmlns:a="{A}"/>'.encode()
        cases['theme override'] = parts
        for owner, primary in (('slideLayouts/slideLayout1', ('slideMaster', '../slideMasters/slideMaster1.xml')),
                               ('slideMasters/slideMaster1', ('theme', '../theme/theme1.xml'))):
            parts = self.package()
            directory, stem = owner.split('/')
            parts[f'ppt/{directory}/_rels/{stem}.xml.rels'] = rels(primary, ('themeOverride', '../theme/themeOverride1.xml'))
            parts['ppt/theme/themeOverride1.xml'] = f'<a:themeOverride xmlns:a="{A}"/>'.encode()
            cases['theme override on ' + directory] = parts
        cases['out of range effect index'] = self.package([slide(shape('bad-index', idx=99))])
        cases['mixed glow and shadow'] = self.package(themes=[theme(['<a:effectLst/>', SHADOW.replace('</a:effectLst>', '<a:glow/></a:effectLst>')])])
        cases['mixed 3D and shadow'] = self.package(themes=[theme(['<a:effectLst/>', SHADOW + '<a:scene3d/>'])])
        parts = self.package()
        parts['ppt/theme/theme1.xml'] = b'<broken'
        cases['malformed theme XML'] = parts
        for name, parts in cases.items():
            with self.subTest(case=name):
                self.output.unlink(missing_ok=True)
                self.write_package(parts)
                original = self.generated.read_bytes()
                expected_error = ET.ParseError if name == 'malformed theme XML' else ValueError
                with self.assertRaises(expected_error):
                    exporter.normalize_generated_pptx(self.svg, self.generated, self.output)
                self.assertFalse(self.output.exists())
                self.assertEqual(self.generated.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
