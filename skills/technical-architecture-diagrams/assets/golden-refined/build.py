"""One author-controlled scientific scene, three native vector backends.
Fixed four-sublayer S=2 AttnRes instance; no general-layout claim.
"""
from pathlib import Path
import argparse, json, math, xml.etree.ElementTree as E, hashlib
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path.cwd()/'attnres-refined');ap.add_argument('--facts',type=Path,default=P/'facts.json' if (P/'facts.json').exists() else P.parent/'semantics/facts.json');a=ap.parse_args();R=a.out;R.mkdir(parents=True,exist_ok=True)
C={'ink':'#20252b','red':'#96505b','blue':'#d2e3f3','orange':'#fce0b9','green':'#dce8cc','muted':'#52606c'}
items=[]; boxes={};edges=[];panel='page'
def shape(id,x,y,w,h,kind='rect',fill='white',stroke='ink',dash=False,radius=4):
 d=dict(type=kind,id=id,x=x,y=y,w=w,h=h,fill=C.get(fill,fill),stroke=C.get(stroke,stroke),dash=dash,radius=radius,panel=panel);items.append(d);boxes[id]=[x,y,w,h];return id
def text(id,s,x,y,w,h,size=23,italic=False,bold=False,muted=False):
 items.append(dict(type='text',id=id,s=s,x=x,y=y,w=w,h=h,size=size,italic=italic,bold=bold,color=C['muted' if muted else 'ink'],panel=panel))
def box(id,s,cx,cy,w=176,h=44,fill='white',size=25):
 shape(id,cx-w/2,cy-h/2,w,h,fill=fill);text(id+'-label',s,cx-w/2,cy-h/2,w,h,size)
def circle(id,s,cx,cy,key='red',r=16):
 shape(id,cx-r,cy-r,2*r,2*r,'circle',stroke=key);text(id+'-label',s,cx-r,cy-r,2*r,2*r,25)
def dot(id,x,y):shape(id,x-1.5,y-1.5,3,3,'circle',fill='ink',stroke='none',radius=0)
def edge(id,source,target,points,key='ink',arrow=True,dash=False,role='data'):
 d=dict(type='edge',id=id,source=source,target=target,points=points,color=C[key],arrow=arrow,dash=dash,role=role,panel=panel);items.append(d);edges.append(d)
def query(id,target,x,y,tx,ty):
 box(id,'w',x,y,27,26,'green',22)
 edge(id+'-edge',id,target,[(x+13.5,y),(tx,ty)],'red',role='query')
shape('canvas',0,0,1600,900,fill='white',stroke='none',radius=0)
panel='standard'
shape('s-frame',40,82,290,651,stroke='ink',dash=True,radius=16)
F={1:620,2:475,3:330,4:185};A={1:692,2:547,3:402,4:257,5:105}
cx=190
box('s-v0','Embedding',cx,777,200,44,'#f1f1f1',25)
for j in range(1,6):circle(f's-a{j}','+',cx,A[j],'ink',14)
edge('s-embed','s-v0','s-a1',[(cx,755),(cx,A[1]+14)])
for j in range(1,5):
 box(f's-F{j}','Attention' if j%2 else 'MoE',cx,F[j],176,44,'blue' if j%2 else 'orange')
 edge(f's-input{j}',f's-a{j}',f's-F{j}',[(cx,A[j]-14),(cx,F[j]+22)])
 dot(f's-v{j}',cx,F[j]-33)
 edge(f's-raw{j}',f's-F{j}',f's-v{j}',[(cx,F[j]-22),(cx,F[j]-33)],arrow=False)
 edge(f's-direct{j}',f's-v{j}',f's-a{j+1}',[(cx,F[j]-33),(cx,A[j+1]+14)])
 edge(f's-skip{j}',f's-a{j}',f's-a{j+1}',[(cx-14,A[j]),(77,A[j]),(77,A[j+1]),(cx-14,A[j+1])],role='unit_residual')
text('s-output','Output',125,3,130,35,29)
edge('s-top','s-a5',None,[(cx,A[5]-14),(cx,64)])
text('s-caption','(a) Standard Residuals',28,820,335,45,25)

panel='full';cx=610;AF={**A,5:74}
shape('f-frame',455,132,277,600,stroke='ink',dash=True,radius=15)
box('f-v0','Embedding',cx,777,200,44,'#f1f1f1',25)
for j in range(1,6):
 circle(f'f-a{j}','1' if j==1 else 'α',cx,AF[j])
 if j>1:query(f'f-w{j}',f'f-a{j}',cx-72,AF[j],cx-16,AF[j])
 if j<5:
  box(f'f-F{j}','Attention' if j%2 else 'MoE',cx,F[j],176,44,'blue' if j%2 else 'orange')
  edge(f'f-input{j}',f'f-a{j}',f'f-F{j}',[(cx,AF[j]-16),(cx,F[j]+22)],'red')
  dot(f'f-v{j}',cx,F[j]-33)
  edge(f'f-raw{j}',f'f-F{j}',f'f-v{j}',[(cx,F[j]-22),(cx,F[j]-33)],'red',False)
for i in range(5):
 sy=777 if i==0 else F[i]-33
 for j in range(i+1,6):
  if j==i+1:pts=[(cx,755 if i==0 else sy),(cx,AF[j]+16)]
  else:
   dy=0;lane=746+22*i;tx=cx+16
   pts=[(cx+100 if i==0 else cx,sy),(lane,sy),(lane,AF[j]+dy),(tx,AF[j]+dy)]
  edge(f'f-history{i}-{j}',f'f-v{i}',f'f-a{j}',pts,'red',role='candidate')
text('f-output','Output',545,3,130,35,29);edge('f-top','f-a5',None,[(610,58),(610,46)],'red')
text('f-caption','(b) Full Attention Residuals',427,820,380,45,25)

panel='block';cx=1290
shape('b-frame1',1108,414,391,318,stroke='ink',dash=True,radius=15)
shape('b-frame2',1108,132,391,232,stroke='ink',dash=True,radius=15)
text('b-block1','Block 1',1119,690,90,26,17,True,muted=True)
text('b-block2','Block 2',1119,337,90,26,17,True,muted=True)
box('b-v0','Embedding',cx,777,200,44,'#f1f1f1',25)
for j in range(1,5):
 box(f'b-F{j}','Attention' if j%2 else 'MoE',cx,F[j],160,44,'blue' if j%2 else 'orange')
 circle(f'b-a{j}','1' if j==1 else 'α',1430,F[j])
 edge(f'b-input{j}',f'b-a{j}',f'b-F{j}',[(1414,F[j]),(1370,F[j])],'red')
 if j>1:
  qy=272 if j==3 else F[j]-42
  box(f'b-w{j}','w',1430,qy,27,26,'green',22)
  edge(f'b-query{j}',f'b-w{j}',f'b-a{j}',[(1430,qy+13),(1430,F[j]-16)],'red',role='query')
 dot(f'b-v{j}',cx,F[j]-33)
 edge(f'b-raw{j}',f'b-F{j}',f'b-v{j}',[(cx,F[j]-22),(cx,F[j]-33)],arrow=False)
circle('b-a5','α',1290,74);query('b-w5','b-a5',1218,74,1274,74)
for j in range(1,6):
 tx,ty=(1430,F[j]) if j<5 else (1290,74);dy=0
 edge(f'b-embed{j}','b-v0',f'b-a{j}',[(1390,777),(1572,777),(1572,ty+dy),(tx+math.sqrt(256-dy*dy),ty+dy)],'red',role='candidate')
for n,first,last,yy in [(1,1,2,390),(2,3,4,122)]:
 circle(f'b-sum{n}','+',cx,yy,'ink',14)
 edge(f'b-sum-current{n}',f'b-v{last}',f'b-sum{n}',[(cx,F[last]-33),(cx,yy+14)],role='raw_sum')
 edge(f'b-sum-partial{n}',f'b-v{first}',f'b-sum{n}',[(cx,F[first]-33),(1170,F[first]-33),(1170,yy),(cx-14,yy)],role='raw_sum')
 text(f'b-sum-note{n}',f'b{n}',1316,yy-28 if n==1 else yy-14,40,24,17,True,muted=True)
 for j in ([3,4,5] if n==1 else [5]):
  tx,ty=(1430,F[j]) if j<5 else (1290,74)
  if n==2:pts=[(cx,yy-14),(cx,90)]
  else:pts=[(cx+14,yy),(1547,yy),(1547,ty),(tx+16,ty)]
  edge(f'b-completed{n}-{j}',f'b-sum{n}',f'b-a{j}',pts,'red',role='candidate')
 sy=F[first]-33
 pts=[(cx,sy),(1519,sy),(1519,F[last]),(1446,F[last])]
 edge(f'b-partial{n}',f'b-v{first}',f'b-a{last}',pts,'red',role='candidate')
text('b-output','Output',1225,3,130,35,29);edge('b-top','b-a5',None,[(1290,58),(1290,46)],'red')
text('b-caption','(c) Block Attention Residuals',1110,820,430,45,25)

panel='operator'
shape('op-frame',830,182,230,309,stroke='muted',dash=True,radius=0)
for key,x in [('K',922),('V',1006)]:
 text('op-'+key+'-title',key,x-20,210,40,30,25,True)
 for i in range(4):shape(f'op-{key}{i}',x-13,255+i*32,26,25,fill='green')
box('op-q','w',861,344,27,27,'green',24);text('op-q-title','Q',842,295,38,32,24,True)
circle('op-dot','×',922,411,'ink',13);circle('op-sum','Σ',965,466,'ink',14)
edge('op-query','op-q','op-dot',[(861,357.5),(861,411),(909,411)],'red')
edge('op-key','op-K3','op-dot',[(922,376),(922,398)],'red')
edge('op-weight','op-dot','op-sum',[(922,424),(922,466),(951,466)],'red')
edge('op-value','op-V3','op-sum',[(1006,376),(1006,466),(979,466)],'red')
edge('op-out','op-sum',None,[(965,480),(965,507)],'red')
text('op-label','AttnRes Op (α)',812,521,266,40,25,True)
text('op-key-note','K = RMSNorm(C)',823,579,252,25,16,muted=True)
text('op-value-note','V = C (raw candidates)',818,608,268,25,16,muted=True)
text('op-soft-note','softmax over depth, per token',801,637,295,25,15,muted=True)
shape('op-target-frame',1190,49,126,48,fill='none',stroke='muted',dash=True,radius=0)
edge('zoom-top','op-frame','op-target-frame',[(1060,182),(1190,49)],'muted',False,True,'callout')
edge('zoom-bottom','op-frame','op-target-frame',[(1060,491),(1190,97)],'muted',False,True,'callout')
panel='page'
edge('divider',None,None,[(392,16),(392,862)],'ink',False,True,'divider')
text('footnote','Four illustrative sublayers; S=2. Block sums contain raw sublayer outputs only; Embedding remains a separate candidate.',50,870,1500,22,13,muted=True)
# A singleton is shown as 1; all other alpha sites have independent learned queries.

def rounded(pts,r=12):
 if len(pts)==2:return 'M '+' L '.join(f'{x:g},{y:g}' for x,y in pts)
 out=[f'M {pts[0][0]:g},{pts[0][1]:g}']
 for i in range(1,len(pts)-1):
  p,q,s=pts[i-1],pts[i],pts[i+1];l1=math.dist(p,q);l2=math.dist(q,s)
  if not l1 or not l2:continue
  rr=min(r,l1/2,l2/2);u=[q[k]+(p[k]-q[k])*rr/l1 for k in (0,1)];v=[q[k]+(s[k]-q[k])*rr/l2 for k in (0,1)]
  k=.5522847498307936
  c1=[u[t]+k*rr*(q[t]-p[t])/l1 for t in (0,1)]
  c2=[v[t]-k*rr*(s[t]-q[t])/l2 for t in (0,1)]
  out.append(f'L {u[0]:g},{u[1]:g} C {c1[0]:g},{c1[1]:g} {c2[0]:g},{c2[1]:g} {v[0]:g},{v[1]:g}')
 out.append(f'L {pts[-1][0]:g},{pts[-1][1]:g}');return ' '.join(out)
def svg():
 ns='http://www.w3.org/2000/svg';ink='http://www.inkscape.org/namespaces/inkscape';E.register_namespace('',ns);E.register_namespace('inkscape',ink)
 root=E.Element('{%s}svg'%ns,width='1600',height='900',viewBox='0 0 1600 900');defs=E.SubElement(root,'defs')
 for key in ['ink','red','muted']:
  m=E.SubElement(defs,'marker',id='arrow-'+key,viewBox='0 0 10 8',refX='10',refY='4',markerWidth='6',markerHeight='5',orient='auto',markerUnits='strokeWidth');E.SubElement(m,'path',d='M0 0 L10 4 L0 8 L2 4 Z',fill=C[key])
 gs={}
 for d in items:
  pan=d['panel']
  if pan not in gs:gs[pan]=E.SubElement(root,'g',id=pan,attrib={'{%s}groupmode'%ink:'layer','{%s}label'%ink:pan})
  g=gs[pan];typ=d['type'];at={'id':d['id']}
  if typ=='text':
   at.update(x=str(d['x']+d['w']/2),y=str(d['y']+d['h']/2+d['size']*.34),fill=d['color'],attribdummy='')
   at.pop('attribdummy');at.update({'font-family':'DejaVu Serif','font-size':str(d['size']),'text-anchor':'middle','font-style':'italic' if d['italic'] else 'normal','font-weight':'bold' if d['bold'] else 'normal'})
   E.SubElement(g,'text',at).text=d['s']
  elif typ in ['rect','circle']:
   at.update(fill=d['fill'],stroke=d['stroke'],attribdummy='');at.pop('attribdummy');at['stroke-width']='1.7'
   if d['dash']:at['stroke-dasharray']='7 6'
   if typ=='rect':at.update(x=str(d['x']),y=str(d['y']),width=str(d['w']),height=str(d['h']),rx=str(d['radius']))
   else:at.update(cx=str(d['x']+d['w']/2),cy=str(d['y']+d['h']/2),r=str(d['w']/2))
   E.SubElement(g,'rect' if typ=='rect' else 'circle',at)
  else:
   at.update(d=rounded(d['points'],0 if d['role'] in ['callout','divider'] else 12),fill='none',stroke=d['color']);at.update({'stroke-width':'1.6','stroke-linecap':'round','stroke-linejoin':'round','data-role':d['role']})
   if d['dash']:at['stroke-dasharray']='3 5'
   if d['source']:at['data-source']=d['source']
   if d['target']:at['data-target']=d['target']
   if d['arrow']:at['marker-end']='url(#arrow-'+next(k for k,v in C.items() if v==d['color'])+')'
   E.SubElement(g,'path',at)
 E.indent(root);E.ElementTree(root).write(R/'scene.svg',encoding='utf-8',xml_declaration=True)
def drawio():
 root=E.Element('mxfile',host='app.diagrams.net',compressed='false');dia=E.SubElement(root,'diagram',id='golden',name='AttnRes');m=E.SubElement(dia,'mxGraphModel',page='1',pageWidth='1600',pageHeight='900',background='#ffffff');rt=E.SubElement(m,'root');E.SubElement(rt,'mxCell',id='0');E.SubElement(rt,'mxCell',id='1',parent='0')
 labels={d['id'][:-6]:d for d in items if d['type']=='text' and d['id'].endswith('-label') and d['id'][:-6] in boxes}
 for d in items:
  typ=d['type'];sty='html=0;';value=d.get('s','')
  if typ=='text' and d['id'].endswith('-label') and d['id'][:-6] in labels:continue
  if typ=='edge':
   sty+='edgeStyle=none;noEdgeStyle=1;rounded=1;arcSize=24;strokeWidth=1.6;strokeColor='+d['color']+';endArrow='+('classic' if d['arrow'] else 'none')+';endSize=6;'
   if d['dash']:sty+='dashed=1;dashPattern=3 5;'
   at={'id':d['id'],'parent':'1','edge':'1','semanticRole':d['role']}
   for side,point,key in [('exit',d['points'][0],'source'),('entry',d['points'][-1],'target')]:
    if d[key]:
     at[key]=d[key];x,y,w,h=boxes[d[key]];sty+=f'{side}X={(point[0]-x)/w};{side}Y={(point[1]-y)/h};{side}Perimeter=0;'
   at['style']=sty;c=E.SubElement(rt,'mxCell',at);g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
   for key,pt in [('source',d['points'][0]),('target',d['points'][-1])]:
    if not d[key]:E.SubElement(g,'mxPoint',x=str(pt[0]),y=str(pt[1]),attrib={'as':key+'Point'})
   arr=E.SubElement(g,'Array',attrib={'as':'points'})
   for x,y in d['points'][1:-1]:E.SubElement(arr,'mxPoint',x=str(x),y=str(y))
  else:
   if typ=='text':sty+=f'text;fillColor=none;strokeColor=none;fontFamily=DejaVu Serif;fontSize={d["size"]};fontColor={d["color"]};fontStyle={(1 if d["bold"] else 0)+(2 if d["italic"] else 0)};align=center;verticalAlign=middle;whiteSpace=nowrap;'
   else:
    sty+=f'shape={"ellipse" if typ=="circle" else "rectangle"};perimeter={"ellipsePerimeter" if typ=="circle" else "rectanglePerimeter"};fillColor={d["fill"]};strokeColor={d["stroke"]};strokeWidth=1.7;rounded={int(d["radius"]>0 and typ=="rect")};absoluteArcSize=1;arcSize={2*d["radius"]};'
    if d['dash']:sty+='dashed=1;dashPattern=7 6;'
    if d['id'] in labels:
     lab=labels[d['id']];value=lab['s'];sty+=f'fontFamily=DejaVu Serif;fontSize={lab["size"]};fontColor={lab["color"]};align=center;verticalAlign=middle;'
   c=E.SubElement(rt,'mxCell',id=d['id'],value=value,vertex='1',parent='1',style=sty);E.SubElement(c,'mxGeometry',x=str(d['x']),y=str(d['y']),width=str(d['w']),height=str(d['h']),attrib={'as':'geometry'})
 E.indent(root);E.ElementTree(root).write(R/'attnres_refined.drawio',encoding='utf-8',xml_declaration=True)
def tikz():
 def hx(s):return {'white':'FFFFFF','none':'FFFFFF'}.get(s,s.lstrip('#'))
 def esc(s):
  for f,t in [('&',r'\&'),('_',r'\_'),('%',r'\%'),('#',r'\#')]:s=s.replace(f,t)
  return s
 lines=[r'\documentclass[border=0pt]{standalone}',r'\usepackage{fontspec,tikz}',r'\setmainfont{DejaVu Serif}[AutoFakeSlant=.15]',r'\usetikzlibrary{arrows.meta}',r'\begin{document}',r'\begin{tikzpicture}[x=.75pt,y=-.75pt,line width=1.275pt,>={Latex[length=4.5pt,width=3.5pt]}]',r'\path[use as bounding box] (0,0) rectangle (1600,900);']
 for idx,d in enumerate(items):
  typ=d['type'];col='col'+str(idx);lines.append(r'\definecolor{'+col+'}{HTML}{'+hx(d.get('color',d.get('stroke','#000000')))+'}')
  if typ=='text':
   size=d['size']*.75;font=f'\\fontsize{{{size}}}{{{size*1.1}}}\\selectfont'+('\\itshape' if d['italic'] else '')+('\\bfseries' if d['bold'] else '')
   lines.append(f'\\node[text={col},inner sep=0pt,font={{{font}}}] at ({d["x"]+d["w"]/2},{d["y"]+d["h"]/2}) {{{esc(d["s"])}}};')
  elif typ in ['rect','circle']:
   fill='fill'+str(idx);lines.append(r'\definecolor{'+fill+'}{HTML}{'+hx(d['fill'])+'}');style='fill='+('none' if d['fill']=='none' else fill)+',draw='+('none' if d['stroke']=='none' else col)+(',dash pattern=on 5.25pt off 4.5pt' if d['dash'] else '')
   if typ=='circle':cmd=f'({d["x"]+d["w"]/2},{d["y"]+d["h"]/2}) circle[radius={d["w"]/2}]'
   else:style+=f',rounded corners={d["radius"]*.75}pt';cmd=f'({d["x"]},{d["y"]}) rectangle ({d["x"]+d["w"]},{d["y"]+d["h"]})'
   lines.append(f'\\path[{style}] {cmd};')
  else:
   sty=f'draw={col},line width=1.2pt'+(',->' if d['arrow'] else '')+(',dash pattern=on 2.25pt off 3.75pt' if d['dash'] else '')+(',rounded corners=9pt' if d['role'] not in ['callout','divider'] else '')
   lines.append('\\draw['+sty+'] '+' -- '.join(f'({x},{y})' for x,y in d['points'])+';')
 lines += [r'\end{tikzpicture}',r'\end{document}'];(R/'attnres_refined.tex').write_text('\n'.join(lines))
svg();drawio();tikz()
scene={'canvas':[1600,900],'facts_sha256':hashlib.sha256(a.facts.read_bytes()).hexdigest(),'scope':'four sublayers, two blocks, S=2; original-inspired geometry, not pixel tracing','items':items}
(R/'scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2))
checks=[]
for j in range(1,6):
 for pre,want in [('f',[f'f-v{i}' for i in range(j)]),('b',{1:['b-v0'],2:['b-v0','b-v1'],3:['b-v0','b-sum1'],4:['b-v0','b-sum1','b-v3'],5:['b-v0','b-sum1','b-sum2']}[j])]:
  got=[e['source'] for e in edges if e['target']==f'{pre}-a{j}' and e['role']=='candidate'];checks.append({'id':f'{pre}{j}','pass':sorted(got)==sorted(want),'actual':got,'expected':want})
for n in [1,2]:
 got=[e['source'] for e in edges if e['target']==f'b-sum{n}'];want=[f'b-v{2*n-1}',f'b-v{2*n}'];checks.append({'id':f'raw-sum{n}','pass':sorted(got)==sorted(want)})
bad=[]
for e in edges:
 if e['role'] not in ['callout']:
  for p,q in zip(e['points'],e['points'][1:]):
   if abs(p[0]-q[0])>1e-6 and abs(p[1]-q[1])>1e-6:bad.append(e['id'])
assert not bad,bad
assert all(c['pass'] for c in checks),checks
(R/'checks.json').write_text(json.dumps({'semantics':checks,'nonorthogonal_data_edges':bad,'note':'2 intentional diagonal zoom leaders are excluded.'},indent=2))
print('Built three native sources; 12 semantic checks; zero diagonal data segments')
