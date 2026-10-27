#!/usr/bin/env python3
"""Check semantics, palette invariance and actual Graph / Inkscape evidence.

Geometry checks use Graph-rendered object/label bounds and engine connector
points, not a character-width estimate. No overall aesthetic score is produced.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def contains(outer,inner,tol=1):
    x,y,w,h=outer;xx,yy,ww,hh=inner
    return xx>=x-tol and yy>=y-tol and xx+ww<=x+w+tol and yy+hh<=y+h+tol
def hits(a,b,box,inset=2):
    x,y,w,h=box;x+=inset;y+=inset;w-=2*inset;h-=2*inset
    if abs(a['x']-b['x'])<.05:
        return x<a['x']<x+w and max(min(a['y'],b['y']),y)<min(max(a['y'],b['y']),y+h)
    if abs(a['y']-b['y'])<.05:
        return y<a['y']<y+h and max(min(a['x'],b['x']),x)<min(max(a['x'],b['x']),x+w)
    return False

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT);a=p.parse_args();out=a.out.resolve()
    facts=read(out/'technical-facts.json'); inp=out/'source-input'
    if not inp.exists():inp=Path(read(out/'evidence/input-manifest.json')['allowed_input_root'])
    cfg=read(inp/'sources/config.json')['text_config'];code=(inp/'sources/model-code.py').read_text()
    provenance=read(inp/'sources/provenance.json');sparse=cfg['sparse_attention_config']
    config_checks={
        'hidden_size_6144':cfg['hidden_size']==6144,
        'decoder_layers_60':cfg['num_hidden_layers']==60,
        'all_60_msa':sparse['sparse_attention_freq']==[1]*60,
        'dense_layers_0_2':[i for i,x in enumerate(cfg['moe_layer_freq']) if x==0]==[0,1,2],
        'moe_layers_3_59':[i for i,x in enumerate(cfg['moe_layer_freq']) if x==1]==list(range(3,60)),
        '64q_4kv_128':(cfg['num_attention_heads'],cfg['num_key_value_heads'],cfg['head_dim'])==(64,4,128),
        'gqa_4_groups_16q':cfg['num_attention_heads']//cfg['num_key_value_heads']==16,
        'no_attention_output_gate':cfg['attention_output_gate'] is False,
        'index_heads_4_width128':(sparse['sparse_num_index_heads'],sparse['sparse_index_dim'])==(4,128),
        'top16_block128_max_local1':(sparse['sparse_topk_blocks'],sparse['sparse_block_size'],sparse['sparse_score_type'],sparse['sparse_local_block'])==(16,128,'max',1),
        '128_experts_top4_shared1':(cfg['num_local_experts'],cfg['num_experts_per_tok'],cfg['n_shared_experts'])==(128,4,1),
        'sigmoid_bias_scale2':(cfg['scoring_func'],cfg['use_routing_bias'],cfg['routed_scaling_factor'])==('sigmoid',True,2.0),
        'expert_width_3072':cfg['intermediate_size']==3072 and cfg['shared_intermediate_size']==3072,
        'snapshot_hash_matches_provenance':sha(inp/'sources/model-code.py')==provenance['sglang_snapshot_sha256'],
        'shared_index_key_1_in_code':'total_num_kv_heads=1' in code,
        'topk_call_renormalizes':'renormalize=True' in code,
        'shared_output_add_in_code':'final_hidden_states = final_hidden_states + shared_output' in code,
        'pre_norm_and_final_norm_declared':all(x in code for x in ['self.input_layernorm','self.post_attention_layernorm','residual_batch.final_norm','self.lm_head'])
    }
    scenes={k:read(out/'source'/f'{k}.layout.json') for k in ['model','msa','moe']}
    all_ids={x['id'] for s in scenes.values() for x in s['nodes']+s['regions']+s['edges']}
    visual=[dict(id=v['id'],fact=v['fact'],objects_present=all(x in all_ids for x in v['objects']),evidence_objects=v['objects']) for v in facts['required_visual_facts']]
    native={};geometry={};svgmetrics={};palette={};edit={}
    for key,s in scenes.items():
        ids=[n['id'] for n in s['nodes']+s['regions']];edgeids=[e['id'] for e in s['edges']]
        trees={pal:ET.parse(out/'native'/f'{key}-{pal}.drawio') for pal in ['paper-clear','blue-neutral']}
        cells={pal:{c.get('id'):c for c in tr.findall('.//mxCell')} for pal,tr in trees.items()}
        native[key]={
            'all_node_ids_unique':len(ids)==len(set(ids)),
            'all_edge_ids_unique':len(edgeids)==len(set(edgeids)),
            'every_edge_connects_real_objects':all(e['source'] in ids and e['target'] in ids for e in s['edges']),
            'no_embedded_image_cells':all('image' not in c.get('style','').lower() for c in cells['paper-clear'].values()),
            'vertices':len(ids),'edges':len(edgeids)
        }
        def semantic(c):return {k:v for k,v in c.attrib.items() if k!='style'},ET.tostring(c.find('mxGeometry')) if c.find('mxGeometry') is not None else None
        def uncoloredstyle(c):
            return ';'.join(v for v in c.get('style','').split(';') if v and v.split('=')[0] not in ['fillColor','strokeColor','fontColor'])
        palette[key]={'same_ids':set(cells['paper-clear'])==set(cells['blue-neutral']),
            'same_labels_endpoints_geometry':all(semantic(c)==semantic(cells['blue-neutral'][id]) for id,c in cells['paper-clear'].items()),
            'same_noncolor_styles':all(uncoloredstyle(c)==uncoloredstyle(cells['blue-neutral'][id]) for id,c in cells['paper-clear'].items())}
        for pal in ['paper-clear','blue-neutral']:
            tag=key+'-'+pal
            states=read(out/'graph'/f'{tag}.rendered-states.json');qa=read(out/'graph'/f'{tag}.runtime-qa.json')
            nmap={n['id']:n for n in s['nodes']+s['regions']}
            vertices=[x for x in states if x['vertex']];edges=[x for x in states if x['edge']]
            textoverflow=[];canvasoverflow=[];diagonals=[];obstructions=[];bordertext=[]
            for st in vertices:
                b=st.get('text_bbox')
                if b and not contains([st['x'],st['y'],st['w'],st['h']],[b['x'],b['y'],b['w'],b['h']]):textoverflow.append(st['id'])
                if not contains([0,0,s['canvas']['width'],s['canvas']['height']],[st['x'],st['y'],st['w'],st['h']]):canvasoverflow.append(st['id'])
            for e in edges:
                pts=e.get('points') or []
                for aa,bb in zip(pts,pts[1:]):
                    if abs(aa['x']-bb['x'])>.05 and abs(aa['y']-bb['y'])>.05:diagonals.append(e['id'])
                    for v in vertices:
                        if v['id'] in [e.get('source'),e.get('target')]:continue
                        vn=nmap.get(v['id'],{});istext=vn.get('shape')=='text'
                        if vn.get('shape')=='region':continue
                        b=v.get('text_bbox') if istext else {k:v[k] for k in ['x','y','w','h']}
                        if b and hits(aa,bb,[b['x'],b['y'],b['w'],b['h']]):obstructions.append({'edge':e['id'],'object':v['id'],'kind':'text' if istext else 'module'})
            for r in s['regions']:
                x,y,w,h=r['bbox']; lines=[({'x':x,'y':y},{'x':x+w,'y':y}),({'x':x+w,'y':y},{'x':x+w,'y':y+h}),({'x':x+w,'y':y+h},{'x':x,'y':y+h}),({'x':x,'y':y+h},{'x':x,'y':y})]
                for v in vertices:
                    if not v.get('text_bbox'):continue
                    b=v['text_bbox']
                    if any(hits(aa,bb,[b['x'],b['y'],b['w'],b['h']],1) for aa,bb in lines):bordertext.append({'region':r['id'],'text':v['id']})
            geometry[tag]={'source':'actual Graph states, label bounding boxes and edge absolutePoints; corners are rounded in the exported SVG',
                'label_overflow':textoverflow,'canvas_overflow':canvasoverflow,'nonorthogonal_segments':sorted(set(diagonals)),
                'edge_obstructions':list({json.dumps(x,sort_keys=True):x for x in obstructions}.values()),'region_border_label_intersections':bordertext,
                'javascript_errors':qa['javascript_errors']}
            r=ET.parse(out/'figures'/f'{tag}.svg').getroot();counts={x:sum(1 for e in r.iter() if e.tag.rsplit('}',1)[-1]==x) for x in ['text','foreignObject','image','path','rect','ellipse']}
            bounds={row[0]:list(map(float,row[1:])) for row in csv.reader((out/'evidence'/f'{tag}.inkscape-bounds.csv').read_text().splitlines())}
            line_candidates={}
            for n in s['nodes']:
                for line in n['label'].split('\n'):line_candidates.setdefault(line,[]).append(n)
            ink_overflow=[]
            for el in r.iter():
                if el.tag.rsplit('}',1)[-1]!='text':continue
                line=''.join(el.itertext()); bb=bounds.get(el.get('id'))
                if bb is None or not any(contains(n['bbox'],bb) for n in line_candidates.get(line,[])):
                    ink_overflow.append({'text':line,'bounds':bb})
            svgmetrics[tag]=dict(**counts,has_embedded_native_model=r.get('content') is not None,viewBox=r.get('viewBox'),inkscape_query_executed=True,inkscape_measured_text_outside_assigned_object=ink_overflow)
            if pal=='paper-clear':
                et=qa['edit_test'];origids=set(cells[pal]);edtree=ET.parse(out/'graph'/f'{tag}.edited.drawio');edcells={c.get('id'):c for c in edtree.findall('.//mxCell')}
                edit[key]={'actual_mouse_drag':et['moved'],'attached_edges_followed':et['edge_points_changed'],'unrelated_nodes_changed':qa['unrelated_nodes_changed'],
                    'ids_preserved':origids==set(edcells),'edge_endpoints_preserved':all((e.get('source'),e.get('target'))==(edcells[id].get('source'),edcells[id].get('target')) for id,e in cells[pal].items() if e.get('edge')=='1'),
                    'reserialized':et['native_xml_reserialized'],'limitation':'Fixed waypoints remain fixed on an arbitrary drag and can create diagonal edge segments in the separate edit proof. Automatic reflow is not claimed.'}
    semantic_checks={
        'attention_residual_origins':all(any(e['id']==p+'_attn_residual' and e['source']==p+'_input' and e['target']==p+'_add_attn' for e in scenes['model']['edges']) for p in ['dense','moe']),
        'ffn_residual_origins':all(any(e['id']==p+'_ffn_residual' and e['source']==p+'_add_attn' and e['target']==p+'_add_ffn' for e in scenes['model']['edges']) for p in ['dense','moe']),
        'separate_index_and_main_keys':all(x in all_ids for x in ['index_keys','content_kv']),
        'weight_dependency_drawn':any(e['source']=='unbiased_weights' and e['target']=='weighted_sum' for e in scenes['moe']['edges']),
        'shared_bypasses_routed_mixing':any(e['source']=='shared_expert' and e['target']=='shared_add' for e in scenes['moe']['edges']) and not any(e['source']=='shared_expert' and e['target'] in ['unbiased_weights','weighted_sum','routed_scale'] for e in scenes['moe']['edges'])
    }
    source_coverage=[
        {'claim':'Input modalities / text output / MSA throughout / auxiliary DSpark','status':'corroborated','source':'supplied README, Model at a Glance; DSpark-not-extra-layers boundary also supplied facts'},
        {'claim':'Depth, hidden width, layer split, heads, block/index settings, experts and routing hyperparameters','status':'verified_in_pinned_config','source':'sources/config.json / text_config'},
        {'claim':'Shared index K distinct from content K/V; norms and terminal LM path; shared expert add','status':'corroborated_in_model_code','source':'model-code.py lines730–894,1690–1833,1882–1888,1955–1959,2092–2110,603–656'},
        {'claim':'Causal index score eligibility; fully-future−∞; local within Top16 budget; exact selected content attention','status':'provided_facts_only_beyond_config','source':'technical-facts.json facts4–5; full MSA paper/backend kernels not supplied'},
        {'claim':'Correction bias selection-only; original unbiased selected scores renormalized','status':'provided_facts_with_api_parameter_corroboration','source':'technical-facts.json fact6; model-code.py TopK call443–452 sets sigmoid/correction/renormalize but TopK internals are not supplied'}
    ]
    allgeometry=all(not any(v for k,v in x.items() if k!='source') for x in geometry.values())
    passed=allgeometry and all(config_checks.values()) and all(semantic_checks.values()) and all(v['objects_present'] for v in visual) and all(all(v.values()) for v in palette.values()) and all(not x['inkscape_measured_text_outside_assigned_object'] for x in svgmetrics.values())
    report={'candidate_status':'agent_self_check_passed' if passed else 'needs_local_revision',
        'not_user_approved':True,'config_and_source_checks':config_checks,'source_coverage':source_coverage,
        'visual_fact_coverage':visual,'visual_coverage_count':{'present':sum(x['objects_present'] for x in visual),'required':len(visual),'note':'Existence is checked separately from the recorded visual/semantic review; counts alone are not a quality score.'},
        'semantic_endpoint_checks':semantic_checks,'native':native,'palette_invariance':palette,'geometry':geometry,'svg':svgmetrics,'edit_probes':edit,
        'not_run':['Full draw.io EditorUi/Desktop','Inkscape GUI dragging','PDF page export/inspection','PPT/PPTX insertion and editing','Model inference or weight loading','Independent full-paper verification','User aesthetic/golden acceptance','Automatic layout generalization'],
        'quality_boundary':'The views remain a module-and-flow abstraction. Source/endpoint/geometry checks and engine execution do not establish user aesthetic approval or golden quality.'}
    (out/'evidence/final-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'config_passed':sum(config_checks.values()),'config_total':len(config_checks),'geometry_clean':allgeometry,'visual_facts_present':report['visual_coverage_count'],'obstructions':{k:v['edge_obstructions'] for k,v in geometry.items() if v['edge_obstructions']}},ensure_ascii=False))

if __name__=='__main__':main()
