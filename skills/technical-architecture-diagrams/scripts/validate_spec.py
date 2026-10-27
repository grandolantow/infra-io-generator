#!/usr/bin/env python3
import json,sys
from pathlib import Path

def validate(d):
    errors=[]
    for key in ['id','title','source_url','facts','baseline','proposed']:
        if not d.get(key):errors.append('Missing '+key)
    for name in ['baseline','proposed']:
        g=d.get(name,{})
        ids=[n.get('id') for n in g.get('nodes',[])]
        if len(ids)!=len(set(ids)):errors.append(name+': duplicate node IDs')
        for e in g.get('edges',[]):
            if e.get('from') not in ids or e.get('to') not in ids:errors.append(name+': dangling edge '+str(e))
            if e.get('kind')=='state_update' and e.get('temporal_scope')=='same_step':errors.append(name+': same-step state dependency must use state_write/data, not delayed state_update: '+str(e))
        for n in g.get('nodes',[]):
            if not n.get('label'):errors.append(name+': empty label '+str(n.get('id')))
    for f in d.get('facts',[]):
        if not f.get('id') or not f.get('statement') or not f.get('locator'):errors.append('Incomplete fact '+str(f.get('id')))
    return errors

if __name__=='__main__':
    d=json.loads(Path(sys.argv[1]).read_text());e=validate(d)
    warnings=[{'scenario':name,'edge':x['from']+'>'+x['to'],'kind':'state_update_temporal_scope_requires_source_review'} for name in ['baseline','proposed'] for x in d.get(name,{}).get('edges',[]) if x.get('kind')=='state_update' and x.get('temporal_scope') not in ['next_step','next_iteration','same_step']]
    print(json.dumps({'status':'structural_contract_only','errors':e,'warnings':warnings,'scientific_accuracy':'requires_source_review'},ensure_ascii=False))
    sys.exit(bool(e))
