import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import jsonschema
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prepare_brief',ROOT/'tools/prepare_diagram_brief.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class BriefTests(unittest.TestCase):
    def brief(self):
        return {'schema_version':1,'task_id':'demo','intent':'model','question':'Explain model structure','audience':'Engineers','facts':[{'id':'f1','statement':'Input connects to output','status':'verified','sources':['public example']}],'target':'ppt','theme':{'palette_policy':'functional colors compatible with theme'},'display_constraints':{'page_orientation':'landscape'},'required_outputs':['drawio','svg'],'language_profile':'diagram-en-prose-zh','preserve':[]}
    def test_preparation_is_not_generation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'input.json').write_text(json.dumps(self.brief()))
            result=m.prepare(p/'input.json',p/'handoff')
            self.assertEqual(result['status'],'prepared_not_executed')
            self.assertEqual(set(x.name for x in (p/'handoff').iterdir()),{'brief.json','agent-task.md'})
    def test_pre_authored_scene_not_high_level_brief(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); b=self.brief();b['source_drawio']='predesigned.drawio';(p/'in.json').write_text(json.dumps(b))
            with self.assertRaises(jsonschema.ValidationError):m.prepare(p/'in.json',p/'out')
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'in.json').write_text(json.dumps(self.brief()));(p/'out').mkdir();(p/'out/user.txt').write_text('preserve')
            with self.assertRaises(ValueError):m.prepare(p/'in.json',p/'out')
            self.assertEqual((p/'out/user.txt').read_text(),'preserve')

    def test_variant_count_explicit_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); b=self.brief(); b['variant_count']=4
            (p/'in.json').write_text(json.dumps(b)); m.prepare(p/'in.json',p/'four')
            self.assertEqual(json.loads((p/'four/brief.json').read_text())['variant_count'],4)
            b['variant_count']=0;(p/'in.json').write_text(json.dumps(b))
            with self.assertRaises(jsonschema.ValidationError): m.prepare(p/'in.json',p/'zero')
