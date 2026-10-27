"""Validate source geometry, native endpoints, and available rendered routes."""
from pathlib import Path
import argparse,json,math,xml.etree.ElementTree as E
ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);a=ap.parse_args();r=a.root
s=json.loads((r/'scene.json').read_text());checks=json.loads((r/'checks.json').read_text());assert all(c['pass'] for c in checks['semantics'])
items={d['id']:d for d in s['items']};cells={c.get('id'):c for c in E.parse(r/'attnres_refined.drawio').findall('.//mxCell')};errors=[]
for d in s['items']:
 if d['type']!='edge':continue
 c=cells[d['id']]
 assert c.get('source')==d['source'] and c.get('target')==d['target'],d['id']
 if d['role']!='callout':
  for p,q in zip(d['points'],d['points'][1:]):
   if abs(p[0]-q[0])>1e-6 and abs(p[1]-q[1])>1e-6:errors.append(d['id'])
assert not errors,errors
rendered=r/'attnres_drawio.rendered-states.json';runtime_result=None
if rendered.exists():
 bad=[]
 for d in json.loads(rendered.read_text()):
  if not d['edge'] or items[d['id']]['role']=='callout':continue
  pts=d.get('points') or []
  for p,q in zip(pts,pts[1:]):
   if abs(p['x']-q['x'])>.05 and abs(p['y']-q['y'])>.05:bad.append(d['id'])
 assert not bad,bad
 runtime_result={'nonorthogonal_data_segments':bad}
qa={'candidate_and_raw_sum_checks':len(checks['semantics']),'passed':True,'source_nonorthogonal_data_edges':errors,'native_endpoints_match_scene':True,'rendered_geometry':runtime_result,'scope':'This checks geometry and source contracts, not user aesthetic acceptance.'}
(r/'routing-qa.json').write_text(json.dumps(qa,indent=2));print(json.dumps(qa))
