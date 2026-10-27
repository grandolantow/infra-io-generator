#!/usr/bin/env python3
"""Actual native-label edit and re-export probe, separate from the formal figure."""
from pathlib import Path
import argparse,json,os,subprocess,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT);p.add_argument('--chrome',default=os.environ.get('CHROME_BINARY'));p.add_argument('--node',default='node');a=p.parse_args()
    out=a.out.resolve();probe=out/'evidence/label-probe';probe.mkdir(exist_ok=True)
    base=ET.parse(out/'native/moe-paper-clear.drawio');old={c.get('id'):c for c in base.findall('.//mxCell')}
    target='original_score_label';original_value=old[target].get('value');old[target].set('value','unbiased scores s_e')
    path=probe/'moe-label.drawio';base.write(path,encoding='utf-8',xml_declaration=True)
    run=subprocess.run([a.node,str(ROOT/'runtime/export.mjs'),'--input',str(path),'--out',str(probe/'moe-label'),'--graph-js',str(ROOT/'runtime/app.min.js'),'--chrome',a.chrome,'--label-mode','plain'],capture_output=True,text=True,check=True)
    (probe/'command-output.json').write_text(run.stdout)
    orig=ET.parse(out/'native/moe-paper-clear.drawio');before={c.get('id'):c for c in orig.findall('.//mxCell')}
    def geom(c):
        g=c.find('mxGeometry');return ET.tostring(g) if g is not None else None
    ids=before.keys()==old.keys();endpoints=all((v.get('source'),v.get('target'))==(old[k].get('source'),old[k].get('target')) for k,v in before.items());positions=all(geom(v)==geom(old[k]) for k,v in before.items())
    svg=ET.parse(probe/'moe-label.svg');text=' '.join(''.join(e.itertext()) for e in svg.getroot().iter() if e.tag.rsplit('}',1)[-1]=='text')
    qa={'edited_id':target,'old_label':original_value,'new_label':'unbiased scores s_e','actual_graph_export':True,'label_visible_in_svg':'unbiased scores s_e' in text,'all_ids_unchanged':ids,'all_edge_endpoints_unchanged':endpoints,'all_object_geometry_unchanged':positions,'scope':'A copied native XML label was edited and rendered again. The formal figure and authoring template were not overwritten.'}
    (out/'evidence/label-probe.json').write_text(json.dumps(qa,indent=2)+'\n');print(json.dumps(qa))

if __name__=='__main__':main()
