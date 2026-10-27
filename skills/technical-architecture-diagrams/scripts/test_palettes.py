#!/usr/bin/env python3
"""Run with python scripts/test_palettes.py. No rendering/runtime needed."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from resolve_palette import resolve, output, flatten, contrast, DEFAULT_CONFIG
from apply_palette import apply_svg, apply_drawio

class Palettes(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(resolve()['palette'],'paper-clear')
        self.assertEqual(resolve('ppt')['palette'],'paper-clear')
        t=resolve('ppt','huawei-plain')
        self.assertEqual(t['palette'],'huawei-plain')
        self.assertEqual(t['tokens']['accent']['primary'],'#C00000')
        self.assertEqual(t['tokens']['text']['primary'],'#1D1D1A')
        for role in ('compute','state','communication','rank0','rank1'):
            self.assertEqual(t['tokens'][role]['fill'],'#F2F4F6')
    def test_override(self):
        self.assertEqual(resolve('ppt','paper-vivid')['palette'],'paper-vivid')
        self.assertEqual(resolve('paper','huawei-plain')['palette'],'huawei-plain')
        self.assertEqual(resolve('ppt','blue-neutral')['palette'],'blue-neutral')
    def test_custom(self):
        custom={'accent':{'primary':'#a12345'}}
        self.assertEqual(resolve('ppt','custom',custom)['tokens']['accent']['primary'],'#A12345')
        self.assertEqual(resolve('paper','huawei-plain',custom)['tokens']['accent']['primary'],'#A12345')
        self.assertEqual(resolve('ppt',custom=custom)['tokens']['background']['panel'],'#FAFBFC')
    def test_invalid(self):
        for kwargs in ({'target':''},{'target':'screen'},{'palette':'unknown'},{'palette':'custom'},
                       {'custom':{}},{'custom':{'nope':{'primary':'#000000'}}},
                       {'custom':{'accent':{'primary':'red'}}},{'custom':{'text':{'primary':'#FFFFFF'}}},
                       {'custom':{'compute':{'fill':'#000000'}}},{'custom':{'text':{}}}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError): resolve(**kwargs)
    def test_bad_config(self):
        config=json.loads(DEFAULT_CONFIG.read_text())
        del config['palettes']['paper-vivid']['text']['primary']
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'invalid.json';p.write_text(json.dumps(config))
            with self.assertRaises(ValueError): resolve('ppt',config_path=p)
    def test_target_defaults_requires_object(self):
        config=json.loads(DEFAULT_CONFIG.read_text())
        config['target_defaults']=['ppt','paper']
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'invalid.json';p.write_text(json.dumps(config))
            with self.assertRaises(ValueError): resolve('ppt',config_path=p)
    def test_formats(self):
        r=resolve('ppt','huawei-plain')
        self.assertEqual(json.loads(output(r))['tokens'],r['tokens'])
        self.assertIn('--diagram-text-primary: #1D1D1A;',output(r,'css'))
        self.assertIn('fontColor=#1D1D1A;',json.loads(output(r,'drawio'))['compute'])
    def test_primary_contrast(self):
        for name in ('huawei-plain','paper-vivid','paper-clear','blue-neutral'):
            t=resolve(palette=name)['tokens']
            for bg in [*t['background'].values(),*(t[k]['fill'] for k in ('compute','state','communication','rank0','rank1'))]:
                self.assertGreaterEqual(contrast(t['text']['primary'],bg),4.5)
    def test_svg_only_color_patch(self):
        src='<svg xmlns="http://www.w3.org/2000/svg"><!-- #ABCDEF --><rect id="#ABCDEF" x="2" fill="#ABCDEF" style="stroke:#abcdef;stroke-width:2"/><text>#ABCDEF</text></svg>'
        t=flatten(resolve('ppt','huawei-plain')['tokens'])
        expected=src.replace('fill="#ABCDEF"','fill="#F2F4F6"').replace('stroke:#abcdef','stroke:#F2F4F6')
        self.assertEqual(apply_svg(src,{'#ABCDEF':'compute.fill'},t),expected)
        with self.assertRaises(ValueError):apply_svg(src,{'#999999':'compute.fill'},t)
        with self.assertRaises(ValueError):apply_svg(src,{'#ABCDEF':'made.up'},t)
    def test_drawio_only_color_patch(self):
        src='<mxfile><diagram id="page"><mxGraphModel><root><mxCell id="0"/><mxCell id="node" value="red &amp; blue" style="fillColor=#000000;strokeColor=#123456;fontColor=#123456;rounded=1;" parent="0"><mxGeometry x="20" y="40" width="80" height="30" as="geometry"/></mxCell></root></mxGraphModel></diagram></mxfile>'
        t=flatten(resolve('ppt','huawei-plain')['tokens'])
        expected=src.replace('fillColor=#000000','fillColor=#F2F4F6').replace('fontColor=#123456','fontColor=#1D1D1A')
        self.assertEqual(apply_drawio(src,{'node':{'fillColor':'compute.fill','fontColor':'text.primary'}},t),expected)
        for mapping in ({'missing':{'fillColor':'compute.fill'}},{'node':{'x':'compute.fill'}},{'node':{'gradientColor':'compute.fill'}}):
            with self.assertRaises(ValueError):apply_drawio(src,mapping,t)
    def test_svg_quoted_delimiter_preserves_metadata(self):
        t=flatten(resolve('ppt','huawei-plain')['tokens'])
        for quote, other in (("'", '"'), ('"', "'")):
            note=f"fill={other}#ABCDEF{other} >"
            src=f'<svg><rect data-note={quote}{note}{quote} fill={quote}#ABCDEF{quote}/></svg>'
            expected=src.replace(f' fill={quote}#ABCDEF{quote}/>',f' fill={quote}#F2F4F6{quote}/>')
            self.assertEqual(apply_svg(src,{'#ABCDEF':'compute.fill'},t),expected)
            metadata_only=f'<svg><rect data-note={quote}{note}{quote}/></svg>'
            with self.assertRaises(ValueError):
                apply_svg(metadata_only,{'#ABCDEF':'compute.fill'},t)
    def test_drawio_quoted_delimiter_preserves_label(self):
        t=flatten(resolve('ppt','huawei-plain')['tokens'])
        for quote, other in (("'", '"'), ('"', "'")):
            label=f'style={other}fillColor=#ABCDEF;{other} >'
            src=f'<mxGraphModel><root><mxCell id="node" value={quote}{label}{quote} style={quote}fillColor=#ABCDEF;{quote}/></root></mxGraphModel>'
            expected=src.replace(f' style={quote}fillColor=#ABCDEF;{quote}/>',f' style={quote}fillColor=#F2F4F6;{quote}/>')
            self.assertEqual(apply_drawio(src,{'node':{'fillColor':'compute.fill'}},t),expected)
            label_only=f'<mxGraphModel><root><mxCell id="node" value={quote}{label}{quote}/></root></mxGraphModel>'
            with self.assertRaises(ValueError):
                apply_drawio(label_only,{'node':{'fillColor':'compute.fill'}},t)
    def test_reject_compressed(self):
        with self.assertRaises(ValueError):apply_drawio('<mxfile><diagram>compressed-data</diagram></mxfile>',{'a':{'fillColor':'compute.fill'}},flatten(resolve()['tokens']))

if __name__=='__main__': unittest.main(verbosity=2)
