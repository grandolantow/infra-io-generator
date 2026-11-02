import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'skills/technical-architecture-diagrams/scripts/figgenie_export.py'
spec = importlib.util.spec_from_file_location('figgenie_export', PATH)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.svg = self.base / 'fig.svg'
        self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200"><g id="n:a"><rect width="20" height="20"/><text>A</text></g></svg>')
        self.spec = self.base / 'spec.json'
        self.spec.write_text('{}')
        self.upstream = self.base / 'upstream'
        self.upstream.mkdir()
        for cmd in (['init', '-q'], ['config', 'user.name', 'Test'], ['config', 'user.email', 'test@example.invalid']):
            subprocess.run(['git', '-C', str(self.upstream), *cmd], check=True)
        scripts = self.upstream / 'scripts'
        scripts.mkdir()
        code = '''import sys, pathlib, json, zipfile
args=sys.argv[1:]; name=pathlib.Path(__file__).name
if name=='check.py':
 out=pathlib.Path(args[args.index('--out-dir')+1]); stem=pathlib.Path(args[0]).stem
 (out/(stem+'.png')).write_bytes(b'png')
 (out/(stem+'.lint.json')).write_text(json.dumps({'errors':0,'warnings':0,'findings':[]}))
elif name=='svg2pptx.py':
 with zipfile.ZipFile(args[args.index('-o')+1], 'w') as z:
  z.writestr('ppt/slides/slide1.xml', '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>')
elif name=='embed_fonts.py':
 pathlib.Path(args[args.index('-o')+1]).write_bytes(b'output')
'''
        for name in ('spec_validate.py', 'check.py', 'embed_fonts.py', 'svg2pptx.py', 'pptx_check.py'):
            (scripts / name).write_text(code)
        subprocess.run(['git', '-C', str(self.upstream), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.upstream), 'commit', '-qm', 'fixture'], check=True)
        revision = subprocess.check_output(['git', '-C', str(self.upstream), 'rev-parse', 'HEAD'], text=True).strip()
        self.config = self.base / 'config.json'
        self.config.write_text(json.dumps({'upstream_repository':'test fixture','upstream_revision':revision,'skill_path':'.'}))
        self.patch = patch.object(exporter, 'CONFIG', self.config)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def args(self, mode='image', **kwargs):
        d = dict(svg=self.svg,spec=self.spec,upstream=str(self.upstream),out=self.base/mode,
                 output_format=mode,display_intent='paper',png_scale=3,math='omml',overwrite=False)
        d.update(kwargs)
        return argparse.Namespace(**d)

    def test_modes_same_source_no_design(self):
        hashes=[]
        for mode,names in [('image',{'fig.final.svg','fig.png'}),('pptx',{'fig.pptx'}),('both',{'fig.final.svg','fig.png','fig.pptx'})]:
            m=exporter.run_export(self.args(mode))
            self.assertEqual(set(m['outputs']),names)
            self.assertEqual(m['design_invocations'],0)
            hashes.append(m['source_svg_sha256'])
            self.assertEqual(m['visual_review'],'not_run')
        self.assertEqual(len(set(hashes)),1)

    def test_image_has_no_ppt_dependency(self):
        # Remove the optional exporter entirely; image must still succeed.
        (self.upstream/'scripts/svg2pptx.py').unlink()
        (self.upstream/'scripts/pptx_check.py').unlink()
        subprocess.run(['git','-C',str(self.upstream),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.upstream),'commit','-qm','image-only'],check=True)
        config=json.loads(self.config.read_text())
        config['upstream_revision']=subprocess.check_output(['git','-C',str(self.upstream),'rev-parse','HEAD'],text=True).strip()
        self.config.write_text(json.dumps(config))
        with patch.object(exporter, 'normalize_generated_pptx', side_effect=AssertionError('image must not touch PPTX')):
            m=exporter.run_export(self.args())
        self.assertFalse(any('pptx' in x['command'][1] for x in m['commands']))

    def test_refuse_overwrite(self):
        exporter.run_export(self.args())
        with self.assertRaisesRegex(ValueError,'hand edits'):
            exporter.run_export(self.args())
        exporter.run_export(self.args(overwrite=True))

    def test_pptx_staging_failures_preserve_manual_output(self):
        out = self.base / 'pptx'
        out.mkdir()
        manual = out / 'fig.pptx'
        manual.write_bytes(b'user edited presentation')
        with self.assertRaisesRegex(ValueError, 'hand edits'):
            exporter.run_export(self.args('pptx'))
        real = subprocess.run
        for step in ('svg2pptx.py', 'compatibility', 'pptx_check.py', 'source_changed'):
            with self.subTest(step=step):
                svg_bytes = self.svg.read_bytes()
                def run(cmd, **kw):
                    if step == cmd[1].split('/')[-1]:
                        return subprocess.CompletedProcess(cmd, 1, '', 'deliberate tool failure')
                    result = real(cmd, **kw)
                    if step == 'source_changed' and str(cmd[1]).endswith('pptx_check.py'):
                        self.svg.write_bytes(svg_bytes + b'\n')
                    return result
                normalizer = exporter.normalize_generated_pptx
                def normalize(*args):
                    if step == 'compatibility':
                        raise ValueError('deliberate compatibility failure')
                    return normalizer(*args)
                with patch.object(exporter.subprocess, 'run', side_effect=run), patch.object(exporter, 'normalize_generated_pptx', side_effect=normalize):
                    with self.assertRaises((ValueError, RuntimeError)):
                        exporter.run_export(self.args('pptx', overwrite=True))
                self.assertEqual(manual.read_bytes(), b'user edited presentation')
                self.assertEqual(list(out.glob('.pptx-stage-*')), [])
                self.assertEqual(json.loads((out/'manifest.json').read_text())['status'], 'failed')
                self.svg.write_bytes(svg_bytes)

    def test_symlink_output_refused_even_with_permission(self):
        out=self.base/'image'
        out.mkdir()
        (out/'fig.final.svg').symlink_to(self.svg)
        before=self.svg.read_bytes()
        with self.assertRaisesRegex(ValueError,'symlinks'):
            exporter.run_export(self.args(overwrite=True))
        self.assertEqual(self.svg.read_bytes(),before)

    def test_source_directory_refused(self):
        with self.assertRaisesRegex(ValueError,'separate output'):
            exporter.run_export(self.args(out=self.base))

    def test_unsupported_has_failure_manifest(self):
        self.svg.write_text(self.svg.read_text().replace('<g id=', '<filter/><g id='))
        with self.assertRaisesRegex(ValueError,'unsupported'):
            exporter.run_export(self.args())
        self.assertEqual(json.loads((self.base/'image/manifest.json').read_text())['status'],'failed')

    def test_positioned_tspan_rejected(self):
        self.svg.write_text(self.svg.read_text().replace('<text>A</text>', '<text><tspan x="10" dy="12">A</tspan><tspan x="10" dy="12">B</tspan></text>'))
        with self.assertRaisesRegex(ValueError,'tspan'):
            exporter.run_export(self.args('both'))

    def test_nested_groups_rejected(self):
        self.svg.write_text(self.svg.read_text().replace('<rect width=', '<g id="n:nested"><rect width=').replace('</g></svg>', '</g></g></svg>'))
        with self.assertRaisesRegex(ValueError,'nested SVG groups'):
            exporter.run_export(self.args('both'))

    def test_hidden_or_clipped_elements_rejected(self):
        for attr in ('display="none"', 'clip-path="url(#clip)"', 'style="visibility:hidden"', 'style="display : none"', 'filter="url(#f)"'):
            with self.subTest(attr=attr):
                self.svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200"><rect '+attr+' width="20" height="20"/></svg>')
                with self.assertRaisesRegex(ValueError,'unsupported'):
                    exporter.inspect_svg(self.svg)

    def test_changed_upstream_refused(self):
        (self.upstream/'scripts/check.py').write_text('modified')
        with self.assertRaisesRegex(ValueError,'tracked modifications'):
            exporter.run_export(self.args())

    def test_source_change_during_export_fails(self):
        real = subprocess.run
        def run(cmd, **kw):
            result=real(cmd,**kw)
            if str(cmd[1]).endswith('check.py'):
                self.svg.write_text(self.svg.read_text()+'\n')
            return result
        with patch.object(exporter.subprocess,'run',side_effect=run):
            with self.assertRaisesRegex(RuntimeError,'source changed'):
                exporter.run_export(self.args())

    def test_aliases(self):
        for alias,mode in [('ppt','pptx'),('图片','image'),('两种都要','both')]:
            self.assertEqual(exporter.normalize_format(alias),mode)
        with self.assertRaises(ValueError): exporter.normalize_format('pdf')

if __name__ == '__main__': unittest.main()
