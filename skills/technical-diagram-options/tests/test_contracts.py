import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
def module(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
selector=module('select_options');diagram=module('diagram_tool');catalog=module('check_package')
class Contracts(unittest.TestCase):
 def setUp(self):
  self.doc=json.loads((ROOT/'examples/toy-mapping.diagram.json').read_text());self.task=json.loads((ROOT/'examples/toy-mapping.task.json').read_text())
 def test_catalog_references(self):self.assertTrue(catalog.check()['valid'])
 def test_covers_all_cases(self):self.assertEqual(catalog.check()['counts']['cited_cases'],50)
 def test_options_not_palette_variants(self):
  r=selector.select(self.task);self.assertGreaterEqual(len(r['options']),2);self.assertEqual(len({tuple(x['structure_modes']) for x in r['options']}),len(r['options']))
 def test_missing_facts_not_invented(self):
  self.task['known_facts']={};r=selector.select(self.task);self.assertTrue(all(x['status']=='conditional' and x['missing_facts'] for x in r['options']))
 def test_assumed_facts_are_conditional(self):
  self.task['known_facts']['mapping']['status']='assumed';r=selector.select(self.task);o=next(x for x in r['options'] if x['rule_id']=='S04');self.assertEqual(o['status'],'conditional');self.assertIn('mapping',o['assumed_facts_needing_confirmation'])
 def numeric_task(self,worked=False,values=False):
  keys=['symbols','equations','example_mapping','entities','operations','dependencies','tensors','axes','transforms']
  known={k:{'value':'symbolic task fact','provenance':'synthetic regression fixture'} for k in keys}
  if values:known['numeric_example']={'value':{'input':[1,2],'convention':'exact integer arithmetic'},'provenance':'synthetic regression fixture'}
  return {'features':['branch_merge','tensor_shapes','equations']+(['worked_example'] if worked else []),'known_facts':known,'constraints':{}}
 def test_symbolic_is_not_numeric_example(self):
  self.assertNotIn('C07',[x['rule_id'] for x in selector.select(self.numeric_task(),20)['options']])
 def test_requested_numeric_example_needs_values(self):
  option=next(x for x in selector.select(self.numeric_task(worked=True),20)['options'] if x['rule_id']=='C07');self.assertEqual(option['status'],'conditional');self.assertIn('numeric_example',option['missing_facts'])
 def test_supported_numeric_example_still_available(self):
  option=next(x for x in selector.select(self.numeric_task(worked=True,values=True),20)['options'] if x['rule_id']=='C07');self.assertEqual(option['status'],'facts_available')
 def test_constraints_respected(self):
  self.task['constraints']['allowed_structures']=['S04'];r=selector.select(self.task);self.assertEqual([x['rule_id'] for x in r['options']],['S04'])
 def test_no_matches_not_fake_options(self):
  self.task['features']=[];self.assertEqual(selector.select(self.task)['options'],[])
 def test_valid_diagram(self):self.assertTrue(diagram.check(self.doc)['valid'])
 def test_bad_semantic_edge(self):
  self.doc['semantic']['edges'][0]['target']='missing';self.assertFalse(diagram.check(self.doc)['valid'])
 def test_wrong_view_endpoint(self):
  self.doc['views'][0]['paths'][0]['target_instance']='v_P2';self.assertFalse(diagram.check(self.doc)['valid'])
 def test_edge_requires_evidence(self):
  self.doc['semantic']['edges'][0]['fact_ids']=[];self.assertFalse(diagram.check(self.doc)['valid'])
 def test_missing_fact_provenance(self):
  del self.doc['semantic']['facts'][0]['provenance'];self.assertFalse(diagram.check(self.doc)['valid'])
 def test_unsafe_output_name(self):
  self.doc['diagram_id']='../../escape';self.assertFalse(diagram.check(self.doc)['valid'])
 def test_style_edit_preserves_semantics(self):
  before=copy.deepcopy(self.doc['semantic']);self.doc['views'][0]['glyphs'][3]['style']['fill']='#FFFFFF';self.assertEqual(before,self.doc['semantic']);self.assertTrue(diagram.check(self.doc)['valid'])
 def test_export_is_native_and_stable(self):
  with tempfile.TemporaryDirectory() as tmp:
   paths=diagram.render(self.doc,tmp);native=E.parse(Path(tmp)/'toy_mapping.drawio');cells=native.findall('.//mxCell');self.assertEqual(len([x for x in cells if x.get('edge')=='1']),2);self.assertTrue(any(x.get('id')=='v_L0' and x.get('vertex')=='1' for x in cells));svg=E.parse(Path(tmp)/'mapping.svg');self.assertIsNotNone(svg.find('.//{http://www.w3.org/2000/svg}text'));self.assertIsNone(svg.find('.//{http://www.w3.org/2000/svg}image'));self.assertTrue(all(Path(p).is_file() for p in paths))
 def test_label_id_collision_rejected(self):
  path=self.doc['views'][0]['paths'][0];path['label']='maps';path['label_position']=[430,230];self.doc['views'][0]['glyphs'][0]['id']=path['id']+'-label';self.assertFalse(diagram.check(self.doc)['valid'])
 def test_gallery_subset_is_partial_not_corrupt(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'one').write_bytes(b'one');sources=[{'source_id':x,'gallery_asset_path':x,'asset_sha256':hashlib.sha256(x.encode()).hexdigest()} for x in ['one','two']];r=catalog.check_galleries(sources,[root]);self.assertEqual(r['errors'],[]);self.assertEqual(r['coverage']['status'],'partial');self.assertEqual(r['coverage']['selected_assets_verified'],1)
 def test_gallery_roots_union_without_merge(self):
  with tempfile.TemporaryDirectory() as tmp:
   roots=[Path(tmp)/'A',Path(tmp)/'B'];sources=[]
   for root,x in zip(roots,['one','two']):root.mkdir();(root/x).write_bytes(x.encode());sources.append({'source_id':x,'gallery_asset_path':x,'asset_sha256':hashlib.sha256(x.encode()).hexdigest()})
   r=catalog.check_galleries(sources,roots);self.assertEqual(r['errors'],[]);self.assertEqual(r['coverage']['status'],'complete');self.assertEqual(r['coverage']['selected_assets_verified'],2)
 def test_gallery_tampering_still_fails(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'one').write_bytes(b'wrong');r=catalog.check_galleries([{'source_id':'one','gallery_asset_path':'one','asset_sha256':hashlib.sha256(b'one').hexdigest()}],[root]);self.assertTrue(r['errors'])
 def test_xml_escaping(self):
  self.doc['views'][0]['glyphs'][3]['label_lines']=['A < B & C'];root=diagram.svg_view(self.doc['views'][0],self.doc);raw=E.tostring(root);E.fromstring(raw);self.assertIn(b'&lt;',raw);self.assertIn(b'&amp;',raw)
 def test_render_warns_not_silently_clips(self):
  self.doc['views'][0]['glyphs'][3]['w']=3;r=diagram.check(self.doc);self.assertTrue(r['valid']);self.assertTrue(any('overflow' in x for x in r['warnings']))
if __name__=='__main__':unittest.main(verbosity=2)
