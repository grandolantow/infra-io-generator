"""Validate this golden's native draw.io semantic connections, not visual quality."""
from pathlib import Path
import argparse,json,hashlib,xml.etree.ElementTree as ET

def check(path):
    root=ET.parse(path);cells=root.findall('.//mxCell');by={c.get('id'):c for c in cells}
    edges=[c for c in cells if c.get('edge')=='1'];checks=[]
    def record(name,ok,detail):checks.append({'name':name,'pass':bool(ok),'detail':detail})
    record('all native edge endpoints exist',all(e.get('source') in by and e.get('target') in by for e in edges),len(edges))
    record('native cell IDs unique',len(by)==len(cells),len(cells))
    actual={}
    for mode,prefix in [('full','f'),('block','b')]:
        actual[mode]=[]
        for site in range(1,6):
            incoming=[e for e in edges if e.get('target')==f'{prefix}_agg{site}' and e.get('semanticRole')!='query_parameter']
            names=[e.get('source') for e in incoming]
            if mode=='full':expected=[f'f_v{i}' for i in range(site)]
            else:expected={1:['b_v0'],2:['b_v0','b_v1'],3:['b_v0','b_sum1'],4:['b_v0','b_sum1','b_v3'],5:['b_v0','b_sum1','b_sum2']}[site]
            actual[mode].append({'site':site,'sources':names})
            record(f'{mode} candidate set at A{site}',sorted(names)==sorted(expected),{'actual':names,'expected':expected})
    for block,raw in [(1,['b_v1','b_v2']),(2,['b_v3','b_v4'])]:
        incoming=[e.get('source') for e in edges if e.get('target')==f'b_sum{block}']
        record(f'block {block} sum has raw outputs only',sorted(incoming)==sorted(raw),incoming)
    for site in range(2,6):
        names=[e.get('source') for e in edges if e.get('target')==f's_agg{site}']
        expected=[f's_v{site-1}',f's_agg{site-1}']
        record(f'Standard unit accumulation at {site}',sorted(names)==sorted(expected),names)
    for prefix in ['f','b']:
        first=by.get(prefix+'_agg1');query_in=[e for e in edges if e.get('target')==prefix+'_agg1' and e.get('semanticRole')=='query_parameter']
        record(prefix+' first singleton is explicitly degenerate',first is not None and first.get('value') in ['1','α','α=1'],{'label':first.get('value') if first is not None else None,'query_inputs':len(query_in)})
    result={'svg_or_png_visual_review':'not_performed_by_this_script','source_drawio':str(path),'source_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'checks':checks,'passed':all(x['pass'] for x in checks),'candidate_connections':actual}
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('path',type=Path);ap.add_argument('--out',type=Path);a=ap.parse_args();r=check(a.path)
    if a.out:a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':r['passed'],'checks':len(r['checks']),'failed':[x for x in r['checks'] if not x['pass']]},ensure_ascii=False));raise SystemExit(not r['passed'])
