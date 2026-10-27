#!/usr/bin/env python3
"""Independent, model-specific native draw.io authoring template.

No prior MiniMax figure, scene, coordinates or generator is an input.
Facts and layout are stored separately. The Graph engine renders all geometry.
"""
from pathlib import Path
import json, hashlib, shutil, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT.parent/'independent-reproduction-input'
SKILL=Path('/root/.codex/skills/remote-skills/skill-6adf2f382d988191b2dc39ad8791ccd6')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def writej(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

class Scene:
    def __init__(self,key,w,h,title):
        self.key=key; self.w=w; self.h=h; self.title=title
        self.nodes=[]; self.edges=[]; self.regions=[]
    def node(self,id,label,x,y,w,h,role='compute',size=23,shape='rect',bold=False,align='center',**attrs):
        n=dict(id=id,label=label,bbox=[x,y,w,h],role=role,size=size,shape=shape,bold=bold,align=align,**attrs)
        self.nodes.append(n); return id
    def text(self,id,label,x,y,w,h,size=21,bold=False,align='left',secondary=False):
        return self.node(id,label,x,y,w,h,'text-secondary' if secondary else 'text',size,'text',bold,align)
    def region(self,id,label,x,y,w,h,role='panel'):
        self.regions.append(dict(id=id,label='',bbox=[x,y,w,h],role=role,size=20,shape='region',bold=False,align='left'))
        self.text(id+'_title',label,x+26,y+16,w-52,34,23,True)
    def edge(self,id,src,tgt,sp=(.5,1),tp=(.5,0),points=None,kind='data',label=''):
        self.edges.append(dict(id=id,source=src,target=tgt,source_port=sp,target_port=tp,points=points or [],kind=kind,label=label))
    def title_block(self,tag,subtitle):
        self.text(self.key+'_title',self.title,60,34,self.w-120,48,35,True)
        self.text(self.key+'_subtitle',subtitle,60,94,self.w-120,38,21,False,secondary=True)
        self.text(self.key+'_tag',tag,self.w-210,38,150,38,21,True,'right',True)
    def as_dict(self):
        return dict(id=self.key,title=self.title,canvas=dict(width=self.w,height=self.h),regions=self.regions,nodes=self.nodes,edges=self.edges)

def model_scene():
    s=Scene('model',1000,2200,'MiniMax M3.1-Flash')
    s.title_block('MODEL','Native multimodal MoE  ·  text hidden size 6144  ·  60 decoder layers')
    s.node('input_text','Text',100,164,220,56,'communication')
    s.node('input_image','Image',390,164,220,56,'communication')
    s.node('input_video','Video',680,164,220,56,'communication')
    s.node('multimodal_fusion','Input embeddings & multimodal fusion\nFrontend internals omitted',245,270,510,74,'communication',23)
    for id,x in [('input_text',210),('input_image',500),('input_video',790)]:
        s.edge(id+'_to_fusion',id,'multimodal_fusion',(.5,1),((x-245)/510 if id=='input_image' else (.2 if x<500 else .8),0),[(x,245),(347 if x<500 else 653 if x>500 else 500,245)])
    for pref,base,title,ffnlabel,role in [
        ('dense',390,'Layers 0–2  ·  repeat ×3','Dense FFN\nSwiGLU', 'state'),
        ('moe',1080,'Layers 3–59  ·  repeat ×57','MoE  ·  Top4 of128 routed +1 shared\nRouted ×2; then add shared  ·  Detail B', 'rank0')]:
        s.region(pref+'_decoder',title,140,base,720,630)
        s.node(pref+'_input','',494,base+68,12,12,'junction',shape='ellipse')
        s.text(pref+'_input_label','x_l',528,base+52,110,38,23)
        s.node(pref+'_norm_attn','Norm',350,base+120,300,50,'panel')
        s.node(pref+'_attention','MiniMax Sparse Attention\n64 Q /4 KV heads  ·  d_head128  ·  Detail A',285,base+205,430,76,'compute',22)
        s.node(pref+'_add_attn','+',476,base+322,48,48,'operator',28,'ellipse')
        s.text(pref+'_h_label','h_l',532,base+325,90,40,23)
        s.node(pref+'_norm_ffn','Norm',350,base+402,300,50,'panel')
        s.node(pref+'_ffn',ffnlabel,265,base+485,470,76,role,22)
        s.node(pref+'_add_ffn','+',476,base+590,48,48,'operator',28,'ellipse')
        s.edge(pref+'_input_to_norm',pref+'_input',pref+'_norm_attn')
        s.edge(pref+'_norm_to_attn',pref+'_norm_attn',pref+'_attention')
        s.edge(pref+'_attn_to_add',pref+'_attention',pref+'_add_attn')
        s.edge(pref+'_attn_residual',pref+'_input',pref+'_add_attn',(0,.5),(0,.5),[(215,base+74),(215,base+346)],'residual')
        s.edge(pref+'_add_to_norm',pref+'_add_attn',pref+'_norm_ffn')
        s.edge(pref+'_norm_to_ffn',pref+'_norm_ffn',pref+'_ffn')
        s.edge(pref+'_ffn_to_add',pref+'_ffn',pref+'_add_ffn')
        s.edge(pref+'_ffn_residual',pref+'_add_attn',pref+'_add_ffn',(1,.5),(1,.5),[(785,base+346),(785,base+614)],'residual')
        s.text(pref+'_residual1_label','residual',168,base+176,100,30,18,False,'left',True)
        s.text(pref+'_residual2_label','residual',749,base+441,100,30,18,False,'left',True)
    s.edge('fusion_to_dense','multimodal_fusion','dense_input')
    s.edge('dense_to_moe','dense_add_ffn','moe_input')
    s.node('final_norm','Final Norm',350,1805,300,56,'panel')
    s.node('lm_head','LM head',350,1910,300,56,'compute')
    s.node('text_output','Text output',350,2015,300,56,'communication')
    s.edge('moe_to_final_norm','moe_add_ffn','final_norm')
    s.edge('norm_to_lm','final_norm','lm_head')
    s.edge('lm_to_output','lm_head','text_output')
    s.text('model_scope','All60 layers use MSA; no attention output gate.\nDSpark is an auxiliary draft, not extra decoder layers; internals omitted.\nVision frontend details and training losses are outside this view.',60,2105,880,75,18,False,'left',True)
    return s

def msa_scene():
    s=Scene('msa',1360,1880,'MiniMax Sparse Attention')
    s.title_block('DETAIL A','One query position i  ·  four GQA groups  ·  selection and exact attention are separate')
    s.node('msa_input','u = Norm(x)',500,165,360,60,'communication')
    s.region('indexer_region','A1  Block indexer',60,305,600,1130)
    s.region('content_region','A2  Exact content attention',720,305,580,1130)
    s.node('index_queries','Index Q\n4 heads ×128\nOne head per GQA group',100,405,235,105,'state',22)
    s.node('index_keys','Index K\n1 shared head ×128\nDistinct from main K',385,405,235,105,'state',22)
    s.node('index_dot','Scaled token dot scores\ns_g(i,j) = q^I_g(i) · k^I(j) / sqrt(128)',130,590,460,94,'state',21)
    s.node('causal_index','Causal index eligibility: j ≤ i\nFully future blocks score −∞',130,770,460,90,'state',22)
    s.node('block_max','Block max over128-token blocks\nb_g(i,b) = max s_g(i,j),  j in b and j ≤ i',130,945,460,94,'state',21)
    s.node('select_blocks','Top16 blocks per group\nLocal block is included within the16-block budget',130,1120,460,104,'rank1',22)
    s.node('block_ids','Selected block IDs S_g(i)',160,1310,400,55,'rank1',22)
    s.node('content_queries','Main Q\n64 heads =4 groups ×16\nd_head128',755,405,250,105,'compute',22)
    s.node('content_kv','Main K / V\n4 group-specific KV heads\nd_head128',1040,405,225,105,'compute',21)
    s.node('selected_kv','Gather group-specific K / V\nK_g[S_g(i)], V_g[S_g(i)]',800,1120,455,104,'compute',22)
    s.node('exact_attention','Exact content attention on selected blocks\nSoftmax(Q_g K_g[S_g]^T / sqrt(128) + causal mask) V_g[S_g]\nCausal j ≤ i in every selected block, including local',750,1310,520,125,'compute',20)
    s.node('attn_output_proj','Concatenate all query heads & output projection',335,1550,690,70,'compute',23)
    s.node('attention_output','Attention output',480,1700,400,62,'communication')
    # All projections receive the same normalized hidden state; ports are distinct.
    for id,x,sp in [('index_queries',217.5,(.2,1)),('index_keys',502.5,(.4,1)),('content_queries',880,(.6,1)),('content_kv',1152.5,(.8,1))]:
        sx=500+360*sp[0]
        s.edge('u_to_'+id,'msa_input',id,sp,(.5,0),[(sx,260),(x,260)])
    s.edge('index_q_to_dot','index_queries','index_dot',(.5,1),(.2,0),[(217.5,550),(222,550)])
    s.edge('index_k_to_dot','index_keys','index_dot',(.5,1),(.8,0),[(502.5,550),(498,550)])
    s.edge('dot_to_causal','index_dot','causal_index')
    s.edge('causal_to_max','causal_index','block_max')
    s.edge('max_to_top16','block_max','select_blocks')
    s.edge('top16_to_ids','select_blocks','block_ids')
    s.edge('ids_to_gather','block_ids','selected_kv',(1,.5),(0,.5),[(690,1337.5),(690,1172)],'selection')
    s.text('selection_edge_label','block IDs',685,1105,110,35,18,False,'left',True)
    s.edge('main_kv_to_gather','content_kv','selected_kv',(.5,1),(.8,0),[(1152.5,1050),(1164,1050)])
    s.edge('gather_to_exact','selected_kv','exact_attention',(.5,1),(.72,0),[(1027.5,1270),(1124.4,1270)])
    s.edge('main_q_to_exact','content_queries','exact_attention',(.5,1),(0,.5),[(880,560),(740,560),(740,1372.5)])
    s.edge('exact_to_outproj','exact_attention','attn_output_proj',(.5,1),(1,.5),[(1010,1490),(1085,1490),(1085,1585)])
    s.edge('outproj_to_output','attn_output_proj','attention_output')
    s.text('msa_scope','Index K is shared across groups; main K / V are group-specific. No attention output gate.\nQ/K normalization, positional encoding and cache implementation details are omitted here.\nThe same MSA mechanism is used in all60 decoder layers.',60,1790,1240,72,18,False,'left',True)
    return s

def moe_scene():
    s=Scene('moe',1420,1780,'Mixture of Experts')
    s.title_block('DETAIL B','Layers3–59  ·  selection bias affects expert choice; original scores determine routed weights')
    s.node('moe_token','z = Norm(h)',540,165,340,65,'communication')
    s.node('router','Router: sigmoid(W_r z)\n128 original scores s_e',100,350,340,90,'state',23)
    s.node('router_bias','Correction bias b_e\nSelection only',495,510,270,75,'rank1',22)
    s.node('expert_select','S = Top4(s + b)\n4 of128 routed experts',100,680,340,90,'rank1',23)
    s.node('selected_experts','Selected experts E_e(z), e in S\n4 routed experts per token\nIntermediate width3072',570,680,350,110,'rank0',22)
    s.node('shared_expert','Shared expert E_s(z)\n1 always-on expert\nIntermediate width3072',1040,680,280,110,'communication',21)
    s.node('unbiased_weights','Unbiased renormalization\nw_e = s_e / Σ_{r in S} s_r\nOriginal s_e; no correction bias',100,955,340,115,'state',22)
    s.node('weighted_sum','Weighted routed sum\nΣ_{e in S} w_e E_e(z)',570,1145,350,95,'rank0',23)
    s.node('routed_scale','Routed scale ×2',570,1315,350,70,'rank0',23)
    s.node('shared_add','+',721,1485,48,48,'operator',29,'ellipse')
    s.node('moe_output','MoE output',570,1615,350,65,'communication')
    s.edge('token_to_router','moe_token','router',(.15,1),(.5,0),[(591,280),(270,280)])
    s.edge('token_to_routed_experts','moe_token','selected_experts',(.6,1),(.5,0),[(744,285),(745,285)])
    s.edge('token_to_shared','moe_token','shared_expert',(.85,1),(.5,0),[(829,280),(1180,280)])
    s.edge('router_to_selection','router','expert_select')
    s.text('original_score_label','original scores s_e',120,535,300,40,21,False,'left',True)
    s.edge('bias_to_selection','router_bias','expert_select',(0,.5),(1,.5),[(470,547.5),(470,725)],'selection')
    s.edge('selection_to_experts','expert_select','selected_experts',(1,.5),(0,.5),[(505,725),(505,735)],'selection')
    s.text('expert_ids_label','IDs',461,682,85,35,18,False,'center',True)
    s.edge('selection_to_weights','expert_select','unbiased_weights',(.5,1),(.5,0),kind='selection')
    s.text('weight_subset_label','selected set S',290,846,180,34,18,False,'left',True)
    s.edge('scores_to_weights','router','unbiased_weights',(0,.5),(0,.5),[(60,395),(60,1012.5)])
    s.text('unbiased_scores_label','s_e',66,866,70,35,20,False,'left',True)
    s.edge('experts_to_sum','selected_experts','weighted_sum')
    s.edge('weights_to_sum','unbiased_weights','weighted_sum',(1,.5),(0,.5),[(515,1012.5),(515,1192.5)])
    s.text('weight_edge_label','w_e',455,1124,65,35,20,False,'left',True)
    s.edge('sum_to_scale','weighted_sum','routed_scale')
    s.edge('scale_to_add','routed_scale','shared_add')
    s.edge('shared_to_add','shared_expert','shared_add',(.5,1),(1,.5),[(1180,1509)])
    s.edge('add_to_moe_output','shared_add','moe_output')
    s.text('shared_bypass_note','Shared output bypasses\nrouted mixing, renormalization\nand the routed ×2 scale.',1005,940,345,94,22,False,'left',True)
    s.text('moe_legend','Solid arrows: token data, scores, weights and expert outputs.   Dashed arrows: selection/control.\nRouted and shared expert boxes are schematic; the128 experts are not drawn individually.',60,1712,1300,57,18,False,'left',True)
    return s

def native(scene,palette):
    t=palette['tokens']; mf=ET.Element('mxfile',host='drawio',version='independent-authoring-v1',compressed='false')
    dg=ET.SubElement(mf,'diagram',id=scene.key,name=scene.title)
    model=ET.SubElement(dg,'mxGraphModel',dx=str(scene.w),dy=str(scene.h),grid='0',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='0',page='1',pageScale='1',pageWidth=str(scene.w),pageHeight=str(scene.h),math='0',shadow='0',background='#FFFFFF')
    root=ET.SubElement(model,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
    def vertex(n):
        r=n['role']; sh=n['shape']
        if r=='operator': fill,stroke='#FFFFFF',t['line']['default']
        elif r=='junction': fill,stroke=t['line']['strong'],t['line']['strong']
        elif r=='panel': fill,stroke=t['background']['panel'],t['line']['default']
        elif r.startswith('text'): fill,stroke='none','none'
        else: fill,stroke=t[r]['fill'],t[r]['stroke']
        style=f'html=0;whiteSpace=wrap;align={n["align"]};verticalAlign=middle;fontFamily=Arial;fontSize={n["size"]};fontColor={t["text"]["secondary"] if r=="text-secondary" else t["text"]["primary"]};fontStyle={1 if n["bold"] else 0};fillColor={fill};strokeColor={stroke};strokeWidth=1.8;spacing=8;'
        if sh=='ellipse': style+='shape=ellipse;perimeter=ellipsePerimeter;'
        elif sh=='region': style+='shape=rectangle;rounded=1;arcSize=4;dashed=1;dashPattern=5 4;strokeWidth=1.5;'
        elif sh=='text': style+='shape=rectangle;spacing=0;'
        else: style+='shape=rectangle;rounded=1;arcSize=7;'
        c=ET.SubElement(root,'mxCell',id=n['id'],value=n['label'],style=style,vertex='1',parent='1',role=r)
        x,y,w,h=n['bbox']; ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),**{'as':'geometry'})
    for n in scene.regions: vertex(n)
    for e in scene.edges:
        sp,tp=e['source_port'],e['target_port']; dash='dashed=1;dashPattern=7 5;' if e['kind']=='selection' else ''
        style=f'edgeStyle=none;orthogonal=1;rounded=0;html=0;endArrow=block;endFill=1;endSize=9;strokeWidth=2;strokeColor={t["line"]["strong"]};fontColor={t["text"]["secondary"]};fontFamily=Arial;fontSize=18;exitX={sp[0]};exitY={sp[1]};entryX={tp[0]};entryY={tp[1]};exitPerimeter=0;entryPerimeter=0;{dash}'
        c=ET.SubElement(root,'mxCell',id=e['id'],value=e['label'],style=style,edge='1',parent='1',source=e['source'],target=e['target'],kind=e['kind'])
        g=ET.SubElement(c,'mxGeometry',relative='1',**{'as':'geometry'})
        if e['points']:
            arr=ET.SubElement(g,'Array',**{'as':'points'})
            for x,y in e['points']:ET.SubElement(arr,'mxPoint',x=str(x),y=str(y))
    for n in scene.nodes: vertex(n)
    ET.indent(mf);return ET.tostring(mf,encoding='unicode',xml_declaration=True)

def main():
    scenes=[model_scene(),msa_scene(),moe_scene()]
    for scene in scenes:
        writej(ROOT/'source'/f'{scene.key}.layout.json',scene.as_dict())
        for p in ['paper-clear','blue-neutral']:
            palette=json.loads((ROOT/'palettes'/f'{p}.json').read_text())
            (ROOT/'native'/f'{scene.key}-{p}.drawio').write_text(native(scene,palette))
    # Freeze explicit per-node semantics separately from geometry and color.
    facts=json.loads((INPUT/'technical-facts.json').read_text())
    facts.update(dict(id='minimax-m31-flash-independent',title='MiniMax M3.1-Flash architecture',
        subtitle='Vertical backbone with separately scoped MSA and MoE mechanisms',
        source_url=facts['sources']['config'],source_locator='config at pinned HF revision; supplied SGLang snapshot; supplied technical-facts.json',
        scope_in=['multimodal input boundary','text backbone','pre-norm residual computation','MSA block selection and exact attention','MoE selection and weighting'],
        baseline=None,proposed=dict(name='MiniMax M3.1-Flash',nodes=[dict(id=n['id'],label=n['label'],detail=n['role']) for s in scenes for n in s.nodes if n['shape']!='text'],edges=[dict(**{'from':e['source'],'to':e['target']},kind=e['kind'],label=e['label']) for s in scenes for e in s.edges]),
        mechanism_notes=['MSA main Q/K/V and shared index K are distinct objects.','The shared expert bypasses routed mixing and scale.'],
        uncertainties=['The MSA paper itself is not present among the permitted local sources. Algorithm constraints beyond config/model-code are transcribed from the supplied facts, not independently checked against the full paper.','The supplied SGLang file delegates top-k scoring and sparse attention kernels to other modules which are not supplied.']))
    facts['facts']=[dict(id=f'F{i+1:02}',statement=v,locator='technical-facts.json / facts / '+str(i)) for i,v in enumerate(facts['facts'])]
    facts['required_visual_facts']=[
        dict(id='V01',fact='Text/image/video fuse before text backbone; text output',objects=['input_text','input_image','input_video','multimodal_fusion','text_output']),
        dict(id='V02',fact='60 MSA decoder layers, hidden6144; dense0–2, MoE3–59',objects=['model_subtitle','dense_decoder_title','moe_decoder_title','model_scope']),
        dict(id='V03',fact='Both pre-norm stages and each identity residual',objects=[p+'_'+x for p in ['dense','moe'] for x in ['input','norm_attn','attention','add_attn','norm_ffn','ffn','add_ffn','attn_residual','ffn_residual']]),
        dict(id='V04',fact='Final norm then LM head; no attention gate',objects=['final_norm','lm_head','model_scope','msa_scope']),
        dict(id='V05',fact='64Q/4KV/128, four groups with16Q each',objects=['content_queries','content_kv','msa_subtitle']),
        dict(id='V06',fact='4 index Q; one shared128-wide index K distinct from main K',objects=['index_queries','index_keys','msa_scope']),
        dict(id='V07',fact='Scaled token dot scores, causal block max128, future−∞',objects=['index_dot','causal_index','block_max']),
        dict(id='V08',fact='Top16 per group includes local within budget',objects=['select_blocks','block_ids']),
        dict(id='V09',fact='Selected group-specific K/V; exact content attention; causal in all selected blocks',objects=['content_kv','selected_kv','exact_attention','main_q_to_exact','gather_to_exact']),
        dict(id='V10',fact='128 routed/Top4/one shared; token data to all branches',objects=['router','expert_select','selected_experts','shared_expert','token_to_router','token_to_routed_experts','token_to_shared']),
        dict(id='V11',fact='Sigmoid scoring; correction bias affects selection only',objects=['router','router_bias','bias_to_selection']),
        dict(id='V12',fact='Original selected unbiased scores renormalized and fed to weighted sum',objects=['unbiased_weights','scores_to_weights','selection_to_weights','weights_to_sum','weighted_sum']),
        dict(id='V13',fact='Routed sum×2; then shared added outside routed mixing/renorm',objects=['routed_scale','shared_add','shared_to_add','shared_bypass_note']),
        dict(id='V14',fact='DSpark auxiliary draft, not extra decoder layers; internals omitted',objects=['model_scope'])]
    writej(ROOT/'technical-facts.json',facts)
    manifest={'allowed_input_root':str(INPUT),'source_revision':facts['source_revision'],'inputs':{str(p.relative_to(INPUT)):sha(p) for p in sorted(INPUT.rglob('*')) if p.is_file()},'skill_file':str(SKILL/'SKILL.md'),'skill_sha256':sha(SKILL/'SKILL.md'),'independence':'No prior generated MiniMax diagrams, scenes, coordinates, generator or evaluation was read. This model-specific template was authored from the permitted facts and source text.'}
    writej(ROOT/'evidence'/'input-manifest.json',manifest)
    print(json.dumps({'scenes':[s.key for s in scenes],'native_files':6,'required_visual_facts':len(facts['required_visual_facts'])}))

if __name__=='__main__':main()
