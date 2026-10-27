"""Golden-calibrated native draw.io authoring; no raster or hand-authored SVG.
Shared row/panel template supplies geometry; mxGraph supplies shapes/edges/export.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import json,hashlib,argparse
R=Path(__file__).resolve().parent; W,H=1600,900
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir',type=Path,required=True)
ap.add_argument('--facts',type=Path,default=R.parent/'semantics/facts.json')
args=ap.parse_args();O=args.output_dir.resolve();O.mkdir(parents=True,exist_ok=True)
C={'ink':'#1d2329','blue':'#cee0f2','orange':'#ffe0b5','green':'#d9e7c8','red':'#9b535c','gray':'#66717a'}
class Diagram:
 def __init__(self):
  self.file=ET.Element('mxfile',host='app.diagrams.net',version='golden-native-1',compressed='false')
  page=ET.SubElement(self.file,'diagram',id='attnres-golden',name='Standard · Full · Block')
  self.model=ET.SubElement(page,'mxGraphModel',dx='1600',dy='900',grid='1',gridSize='10',page='1',pageScale='1',pageWidth=str(W),pageHeight=str(H),math='0',background='#ffffff')
  self.root=ET.SubElement(self.model,'root');ET.SubElement(self.root,'mxCell',id='0');ET.SubElement(self.root,'mxCell',id='1',parent='0')
  self.box={'1':(0,0,W,H)};self.nodes=[];self.edges=[]
 def v(self,id,value,x,y,w,h,parent='1',style='',role='label',font=22):
  px,py,_,_=self.box[parent]
  s=f'html=0;fontFamily=Microsoft YaHei,Noto Sans SC,Arial;fontSize={font};fontColor={C["ink"]};strokeWidth=1.8;align=center;verticalAlign=middle;whiteSpace=wrap;'+style
  cell=ET.SubElement(self.root,'mxCell',id=id,value=value,style=s,vertex='1',parent=parent,semanticRole=role)
  ET.SubElement(cell,'mxGeometry',x=str(x-px),y=str(y-py),width=str(w),height=str(h),attrib={'as':'geometry'})
  self.box[id]=(x,y,w,h);self.nodes.append({'id':id,'value':value,'role':role,'bbox':[x,y,w,h],'parent':parent})
  return id
 def group(self,id,x,y,w,h,parent='1',frame=False,label=''):
  return self.v(id,label,x,y,w,h,parent,('rounded=1;arcSize=5;container=1;pointerEvents=0;fillColor=none;strokeColor=#77828c;dashed=1;dashPattern=5 5;verticalAlign=top;align=left;spacingLeft=9;fontStyle=2;fontSize=16;' if frame else 'group;container=1;pointerEvents=0;fillColor=none;strokeColor=none;'),role='group')
 def text(self,id,value,x,y,w,h,font=22,parent='1',style=''):
  return self.v(id,value,x,y,w,h,parent,'text;strokeColor=none;fillColor=none;spacing=0;'+style,'label',font)
 def circle(self,id,value,cx,cy,r=15,parent='1',color=None,role='aggregation'):
  return self.v(id,value,cx-r,cy-r,2*r,2*r,parent,f'shape=ellipse;perimeter=ellipsePerimeter;aspect=fixed;fillColor=#ffffff;strokeColor={color or C["ink"]};fontFamily=Georgia;fontSize=25;',role,25)
 def edge(self,id,source,target,pts=(),parent='1',color=None,exit=(.5,0),entry=(.5,1),arrow=True,dashed=False,role='data',width=1.9):
  px,py,_,_=self.box[parent]
  s=f'edgeStyle=none;noEdgeStyle=1;rounded=1;arcSize=8;html=0;strokeWidth={width};strokeColor={color or C["ink"]};endArrow={"classic" if arrow else "none"};endSize=7;endFill=1;exitX={exit[0]};exitY={exit[1]};exitPerimeter=1;entryX={entry[0]};entryY={entry[1]};entryPerimeter=1;'
  if dashed:s+='dashed=1;dashPattern=3 4;'
  cell=ET.SubElement(self.root,'mxCell',id=id,source=source,target=target,style=s,edge='1',parent=parent,semanticRole=role)
  g=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
  if pts:
   arr=ET.SubElement(g,'Array',attrib={'as':'points'})
   for x,y in pts:ET.SubElement(arr,'mxPoint',x=str(x-px),y=str(y-py))
  self.edges.append({'id':id,'source':source,'target':target,'role':role,'waypoints':[list(p) for p in pts]})
 def dot(self,id,x,y,parent):return self.v(id,'',x-2,y-2,4,4,parent,'shape=ellipse;perimeter=ellipsePerimeter;fillColor=#222222;strokeColor=none;','raw_output',1)
D=Diagram()
D.v('page','',0,0,W,H,style='fillColor=#ffffff;strokeColor=none;movable=0;resizable=0;connectable=0;',role='page')
D.text('title','Attention Residuals',45,22,1510,46,34,style='align=left;fontStyle=1;')
D.text('subtitle','同一主干，对比固定残差、逐层注意力与分块注意力',45,76,1510,30,23,style='align=left;fontColor=#52606b;')
# Same y coordinates across all alternatives, as in the paper's architecture comparison.
A={1:697,2:587,3:477,4:367,5:257}; F={1:642,2:532,3:422,4:312}
for key,x,w,title,sub in [('s',40,270,'Standard Residuals','固定单位权重'),('f',350,345,'Full AttnRes','逐个历史子层输出参与选择'),('b',1110,445,'Block AttnRes','已完成块 ＋ 当前块部分和')]:
 D.group(key+'_panel',x,145,w,690)
 D.text(key+'_heading',title,x,142,w,38,27,parent=key+'_panel',style='fontStyle=1;')
 D.text(key+'_sub',sub,x,184,w,28,19,parent=key+'_panel',style='fontColor=#52606b;')
for key,cx in [('s',175),('f',500)]:
 par=key+'_panel';col=C['ink'] if key=='s' else C['red']
 D.v(key+'_v0','Embedding  v₀',cx-85,735,170,44,par,'rounded=1;arcSize=15;fillColor=#f3f3f3;strokeColor=#333333;','embedding',24)
 for i in range(1,6):
  D.circle(f'{key}_agg{i}','+' if key=='s' else ('1' if i==1 else 'α'),cx,A[i],parent=par,color=col)
  if key=='f' and i>1:
   D.v(f'f_query{i}','w'+str(i),cx-76,A[i]-13,28,26,par,'rounded=1;arcSize=12;fillColor='+C['green']+';strokeColor=#455540;','learned_query',17)
   D.edge(f'f_query_edge{i}',f'f_query{i}',f'f_agg{i}',parent=par,color=col,exit=(1,.5),entry=(0,.5),role='query_parameter')
  if i<=4:
   fill=C['blue'] if i%2 else C['orange'];lab='Attention' if i%2 else 'MoE'
   D.v(f'{key}_layer{i}',lab,cx-85,F[i]-22,170,44,par,f'rounded=1;arcSize=13;fillColor={fill};strokeColor=#303740;','sublayer',25)
   D.edge(f'{key}_input{i}',f'{key}_agg{i}',f'{key}_layer{i}',parent=par,color=col)
   D.dot(f'{key}_v{i}',cx,F[i]-37,par)
   D.edge(f'{key}_raw{i}',f'{key}_layer{i}',f'{key}_v{i}',parent=par,color=col,role='raw_sublayer_output',arrow=False)
 for i in range(5):
  source=key+'_v'+str(i)
  if key=='s':
   D.edge(f's_main{i}',source,f's_agg{i+1}',parent=par)
  else:
   for j in range(i+1,6):
    ey=.20+.60*i/max(1,j-2)
    pts=[] if j==i+1 else [(cx+100+12*i,(757 if i==0 else F[i]-37)),(cx+100+12*i,A[j]+30*(ey-.5))]
    D.edge(f'f_history_{i}_{j}',source,f'f_agg{j}',pts,parent=par,color=col,exit=(.5,0) if j==i+1 else(1,.5),entry=(.5,1) if j==i+1 else(1,ey),role='history_candidate')
 if key=='s':
  for i in range(1,5):D.edge(f's_residual{i}',f's_agg{i}',f's_agg{i+1}',[(cx-112,A[i]),(cx-112,A[i+1])],parent=par,exit=(0,.5),entry=(0,.5),role='identity_residual')
 D.text(key+'_out','Output',cx-65,207,130,25,23,parent=par)
 D.edge(key+'_output',key+'_agg5',key+'_out',parent=par,color=col,entry=(.5,1))
 D.text(key+'_count','全部权重 = 1' if key=='s' else '候选数：1 / 2 / 3 / 4 / 5',40 if key=='s' else 350,802,270 if key=='s' else 345,27,18,parent=par,style='fontColor=#52606b;')
# Block has two REAL partial-sum groups. Weighted h feeds F; raw v alone feeds +.
par='b_panel';cx=1280
D.group('block1',1110,503,405,217,parent=par,frame=True,label='Block 1')
D.group('block2',1110,283,405,217,parent=par,frame=True,label='Block 2')
D.v('b_v0','Embedding  v₀',cx-85,735,170,44,par,'rounded=1;fillColor=#f3f3f3;strokeColor=#333333;','embedding',24)
for i in range(1,6):
 local='block1' if i<=2 else 'block2' if i<=4 else par
 D.circle(f'b_agg{i}','1' if i==1 else 'α',cx,A[i],parent=local,color=C['red'])
 if i>1:D.v(f'b_query{i}','w'+str(i),cx-76,A[i]-13,28,26,local,'rounded=1;arcSize=12;fillColor='+C['green']+';strokeColor=#455540;','learned_query',17)
 if i>1:D.edge(f'b_query_edge{i}',f'b_query{i}',f'b_agg{i}',parent=par,color=C['red'],exit=(1,.5),entry=(0,.5),role='query_parameter')
 if i<=4:
  fill=C['blue'] if i%2 else C['orange'];lab='Attention' if i%2 else 'MoE'
  D.v(f'b_layer{i}',lab,cx-85,F[i]-22,170,44,local,f'rounded=1;arcSize=13;fillColor={fill};strokeColor=#303740;','sublayer',25)
  D.edge(f'b_input{i}',f'b_agg{i}',f'b_layer{i}',parent=par,color=C['red'],role='weighted_sublayer_input')
  D.dot(f'b_v{i}',cx if i%2 else cx+110,F[i]-37 if i%2 else F[i],local)
  D.edge(f'b_raw{i}',f'b_layer{i}',f'b_v{i}',parent=par,role='raw_sublayer_output',arrow=False,exit=(.5,0) if i%2 else(1,.5),entry=(.5,1) if i%2 else(0,.5))
# Embedding is a separate candidate at EVERY aggregate.
for j in range(1,6):
 pts=[] if j==1 else [(1490,757),(1490,A[j]-9)]
 D.edge(f'b_embedding_{j}','b_v0',f'b_agg{j}',pts,parent=par,color=C['red'],exit=(.5,0) if j==1 else(1,.5),entry=(.5,1) if j==1 else(1,.2),role='embedding_candidate')
# First raw output of each block is the partial-sum candidate before its second F.
for a,b in [(1,2),(3,4)]:
 D.edge(f'b_partial_{a}_{b}',f'b_v{a}',f'b_agg{b}',parent=par,color=C['red'],role='partial_block_candidate')
# End-of-block sums exclude h and embedding.
for n,first,last,yy,grp in [(1,1,2,495,'block1'),(2,3,4,275,'block2')]:
 D.circle(f'b_sum{n}','+',1367,yy,14,parent=par,role='raw_block_sum')
 D.edge(f'b_addlast{n}',f'b_v{last}',f'b_sum{n}',[(cx+110,yy+28),(1367,yy+28)],parent=par,exit=(.5,0),entry=(.5,1),role='raw_to_block_sum')
 D.edge(f'b_addfirst{n}',f'b_v{first}',f'b_sum{n}',[(1406,F[first]-37),(1406,yy+3)],parent=par,exit=(1,.5),entry=(1,.6),role='partial_to_block_sum')
 D.text(f'b_sumlabel{n}','b₁' if n==1 else 'b₂',1415,yy+9,40,22,19,parent=par,style='align=left;')
 for j in ([3,4,5] if n==1 else [5]):
  lane=1450 if n==1 else 1428
  D.edge(f'b_block{n}_{j}',f'b_sum{n}',f'b_agg{j}',[(lane,yy),(lane,A[j]+(7 if n==1 else 11))],parent=par,color=C['red'],exit=(1,.25),entry=(1,.73 if n==1 else .87),role='completed_block_candidate')
D.text('b_out','Output',1215,207,130,25,23,parent=par)
D.edge('b_output','b_agg5','b_out',parent=par,color=C['red'])
D.text('b_count','S=2；候选数：1 / 2 / 2 / 3 / 3',1110,802,445,27,18,parent=par,style='fontColor=#52606b;')
# Shared attention operator, between Full and Block just like the paper inset.
D.group('op_panel',717,145,328,660)
D.text('op_title','α 算子展开',717,150,328,34,26,parent='op_panel',style='fontStyle=1;')
D.text('op_sub','Full 与 Block 共用',717,190,328,25,19,parent='op_panel',style='fontColor=#52606b;')
D.text('q_title','Q',738,271,45,25,22,parent='op_panel',style='fontFamily=Georgia;fontStyle=2;')
D.v('op_query','wₗ',743,311,34,34,'op_panel','rounded=1;arcSize=8;fillColor='+C['green']+';strokeColor=#33402c;','learned_query',22)
for col,x in [('keys',855),('values',978)]:
 D.text('op_'+col+'_title','K' if col=='keys' else 'V',x-5,245,45,25,23,parent='op_panel',style='fontFamily=Georgia;fontStyle=2;')
 D.group('op_'+col,x,282,34,117,'op_panel')
 for k in range(3):D.v(f'op_{col}_{k}','',x,282+39*k,34,30,'op_'+col,'rounded=1;arcSize=8;fillColor='+C['green']+';strokeColor=#33402c;','key_candidate' if col=='keys' else 'raw_value_candidate',18)
D.text('key_norm','RMSNorm(cᵢ)',884,412,108,25,16,parent='op_panel',style='fontColor=#52606b;')
D.circle('op_dot','×',871,453,16,parent='op_panel',role='query_key_dot')
D.edge('op_q_dot','op_query','op_dot',[(760,453)],parent='op_panel',exit=(.5,1),entry=(0,.5))
D.edge('op_k_dot','op_keys','op_dot',parent='op_panel',exit=(.5,1),entry=(.5,0),role='normalized_keys')
D.v('op_softmax','softmaxᵢ',813,489,116,35,'op_panel','rounded=1;fillColor=#ffffff;strokeColor=#444444;','depth_softmax',20)
D.edge('op_logits','op_dot','op_softmax',parent='op_panel',exit=(.5,1),entry=(.5,0),role='depth_logits')
D.circle('op_sum','Σ',995,557,18,parent='op_panel',color=C['red'],role='weighted_value_sum')
D.edge('op_alpha','op_softmax','op_sum',[(871,557)],parent='op_panel',color=C['red'],exit=(.5,1),entry=(0,.5),role='depth_weights')
D.edge('op_v_sum','op_values','op_sum',parent='op_panel',exit=(.5,1),entry=(.5,0),role='raw_values')
D.text('op_h','hₗ',969,606,60,27,24,parent='op_panel',style='fontFamily=Georgia;')
D.edge('op_result','op_sum','op_h',parent='op_panel',color=C['red'],exit=(.5,1),entry=(.5,0))
D.text('op_equation1','kᵢ = RMSNorm(cᵢ)',722,663,320,28,20,parent='op_panel')
D.text('op_equation2','α = softmaxᵢ(wₗᵀkᵢ)',722,698,320,28,20,parent='op_panel')
D.text('op_equation3','hₗ = Σᵢ αᵢcᵢ',722,733,320,28,23,parent='op_panel')
D.text('op_value_note','cᵢ 为同一 token 的深度候选\nV 保留原值，不归一化',717,775,328,48,17,parent='op_panel',style='fontColor=#52606b;')
D.text('legend','Attention / MoE 仅示意四个子层；Norm 省略。Block 的 b₁=v₁+v₂，b₂=v₃+v₄，不含聚合 h 或 Embedding；首层 α₁=1。',45,839,1510,28,18,style='align=left;')
D.text('source','来源：Attention Residuals · Fig.1 / §3.1–3.2 / Eq.2–6；MoonshotAI 官方伪代码。',45,872,1510,20,15,style='align=left;fontColor=#69747d;')
ET.indent(D.file);out=O/'attention_residuals.drawio';ET.ElementTree(D.file).write(out,encoding='utf-8',xml_declaration=True)
facts=args.facts;manifest={'canvas':[W,H],'vertices':len(D.nodes),'edges':len(D.edges),'renderer':'draw.io native mxGraph XML (SVG not authored by this script)','layout_source':'shared golden template; aligned layer rows and explicitly authored candidate routes','manual_constraints':{'panels':4,'shared_aggregation_y':5,'shared_sublayer_y':4,'block_boundaries':2,'automatic_node_layout':False},'facts_sha256':hashlib.sha256(facts.read_bytes()).hexdigest(),'nodes':D.nodes,'edges':D.edges}
(O/'authoring.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(out,'nodes',len(D.nodes),'edges',len(D.edges))
