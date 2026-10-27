#!/usr/bin/env python3
"""Validate authored diagram IR and export source-editable SVG / native draw.io. No auto-layout."""
import argparse,json,math,re,sys
from pathlib import Path
import xml.etree.ElementTree as E
SAFE_ID=re.compile(r'^[A-Za-z_][A-Za-z0-9_.:-]*$')
def dup(xs):return sorted({x for x in xs if xs.count(x)>1})
def bbox(g):return [g[k] for k in ('x','y','w','h')]
def check(doc):
    errors=[];warnings=[];sem=doc.get('semantic',{});nodes=sem.get('nodes',[]);edges=sem.get('edges',[]);facts=sem.get('facts',[])
    ids=[x.get('id') for x in nodes+edges+facts];nodeids={x.get('id') for x in nodes};edgeby={x.get('id'):x for x in edges};factids={x.get('id') for x in facts}
    if not isinstance(doc.get('diagram_id'),str) or not SAFE_ID.fullmatch(doc['diagram_id']):errors.append('diagram_id must be a safe stable ID')
    if not nodes:errors.append('semantic nodes required')
    if not facts:errors.append('at least one provenance-backed fact required')
    for x in ids:
        if not isinstance(x,str) or not SAFE_ID.fullmatch(x):errors.append(f'invalid semantic ID {x!r}')
    if len(set(ids))!=len(ids):errors.append('semantic IDs must be unique across nodes, edges and facts')
    for f in facts:
        if not f.get('provenance'):errors.append(f"fact {f.get('id')} missing provenance")
    for x in nodes+edges:
        for fid in x.get('fact_ids',[]):
            if fid not in factids:errors.append(f"{x.get('id')}: unknown fact {fid}")
    for edge in edges:
        if not edge.get('fact_ids'):errors.append(f"edge {edge.get('id')}: at least one fact reference required")
        if edge.get('source') not in nodeids or edge.get('target') not in nodeids:errors.append(f"edge {edge.get('id')}: unknown endpoint")
        if not edge.get('relation'):errors.append(f"edge {edge.get('id')}: relation required")
    views=doc.get('views',[])
    if not views:errors.append('at least one view required')
    if len({v.get('id') for v in views})!=len(views):errors.append('duplicate view IDs')
    for v in views:
        vid=v.get('id');canvas=v.get('canvas',{});width=canvas.get('width',0);height=canvas.get('height',0)
        if not isinstance(vid,str) or not SAFE_ID.fullmatch(vid):errors.append(f'invalid view ID {vid!r}')
        if width<=0 or height<=0:errors.append(f'{vid}: canvas must be positive')
        glyphs=v.get('glyphs',[]);paths=v.get('paths',[]);gby={g.get('id'):g for g in glyphs};gids=list(gby)
        if len(gids)!=len(glyphs) or len({x.get('id') for x in glyphs+paths})!=len(glyphs+paths):errors.append(f'{vid}: duplicate instance IDs')
        for g in glyphs:
            gid=g.get('id')
            if not isinstance(gid,str) or not SAFE_ID.fullmatch(gid):errors.append(f'{vid}: invalid glyph ID {gid!r}')
            if g.get('semantic_ref') and g['semantic_ref'] not in nodeids:errors.append(f'{vid}/{gid}: unknown node reference')
            if g.get('shape','rect') not in ('rect','rounded_rect','ellipse','diamond','text'):errors.append(f'{vid}/{gid}: unsupported shape')
            try:
                x,y,w,h=bbox(g)
                if not all(isinstance(z,(int,float)) and math.isfinite(z) for z in (x,y,w,h)) or w<=0 or h<=0:raise ValueError()
            except (KeyError,ValueError,TypeError):errors.append(f'{vid}/{gid}: invalid geometry');continue
            if x<0 or y<0 or x+w>width or y+h>height:warnings.append(f'{vid}/{gid}: outside canvas')
            lines=g.get('label_lines',[g.get('label','')]);font=g.get('style',{}).get('font_size',16)
            if len(lines)*font*1.2>h:warnings.append(f'{vid}/{gid}: label height may overflow')
            for line in lines:
                units=sum(1 if ord(c)>127 else .55 for c in str(line))
                if units*font>w:warnings.append(f'{vid}/{gid}: label width may overflow; render to verify');break
        for p in paths:
            pid=p.get('id');ref=p.get('semantic_ref');pts=p.get('points',[])
            if not isinstance(pid,str) or not SAFE_ID.fullmatch(pid):errors.append(f'{vid}: invalid path ID {pid!r}')
            if ref not in edgeby:errors.append(f'{vid}/{pid}: unknown semantic edge')
            a=gby.get(p.get('source_instance'));b=gby.get(p.get('target_instance'))
            if not a or not b:errors.append(f'{vid}/{pid}: missing instance endpoint')
            elif ref in edgeby and (a.get('semantic_ref')!=edgeby[ref]['source'] or b.get('semantic_ref')!=edgeby[ref]['target']):errors.append(f'{vid}/{pid}: view endpoints disagree with semantic edge')
            if len(pts)<2 or any(len(q)!=2 or not all(isinstance(z,(int,float)) and math.isfinite(z) for z in q) for q in pts):errors.append(f'{vid}/{pid}: at least two finite coordinate pairs required');continue
            for q in pts:
                if q[0]<0 or q[1]<0 or q[0]>width or q[1]>height:warnings.append(f'{vid}/{pid}: route outside canvas');break
            if 'label' in p and 'label_position' not in p:errors.append(f'{vid}/{pid}: explicit label_position required')
            if p.get('label') and pid+'-label' in {x.get('id') for x in glyphs+paths}:errors.append(f'{vid}/{pid}: generated label ID collision')
            # Conservative sampled segment-interior check. Container boundaries are allowed.
            for g in glyphs:
                if g.get('role')=='container' or g.get('id') in (p.get('source_instance'),p.get('target_instance')):continue
                try:x,y,w,h=bbox(g)
                except KeyError:continue
                hit=False
                for q,r in zip(pts,pts[1:]):
                    steps=max(2,int(math.hypot(r[0]-q[0],r[1]-q[1])/3))
                    if any(x+1<q[0]+(r[0]-q[0])*i/steps<x+w-1 and y+1<q[1]+(r[1]-q[1])*i/steps<y+h-1 for i in range(steps+1)):hit=True;break
                if hit:warnings.append(f'{vid}/{pid}: crosses unrelated glyph {g.get("id")}; inspect')
        # A view may deliberately omit facts; require its scope to explain partial coverage.
        if not v.get('scope'):warnings.append(f'{vid}: no scope/omission note')
    return {'valid':not errors,'errors':errors,'warnings':sorted(set(warnings)),'limits':['Geometry checks are conservative warnings, not pixel QA.','No factual correctness, overlap timing, accessibility, typography or empirical effectiveness is proved.']}
def style(g):
    s=g.get('style',{});return {'fill':s.get('fill','white'),'stroke':s.get('stroke','black'),'stroke_width':s.get('stroke_width',1.5),'font_size':s.get('font_size',16),'font_family':s.get('font_family','sans-serif'),'text_color':s.get('text_color','black'),'dashed':s.get('dashed',False)}
def svg_view(v,doc):
    root=E.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','width':str(v['canvas']['width']),'height':str(v['canvas']['height']),'viewBox':f"0 0 {v['canvas']['width']} {v['canvas']['height']}",'role':'img'})
    E.SubElement(root,'title').text=v.get('title',doc['diagram_id']);E.SubElement(root,'desc').text=v.get('scope','')
    E.SubElement(root,'metadata').text=json.dumps({'diagram_id':doc['diagram_id'],'view_id':v['id'],'fact_ids':[f['id'] for f in doc['semantic'].get('facts',[])]})
    if v['canvas'].get('background'):E.SubElement(root,'rect',{'width':'100%','height':'100%','fill':v['canvas']['background']})
    defs=E.SubElement(root,'defs')
    # Containers first, edges second, object labels last. Their IDs persist across exports.
    def draw_g(g):
        s=style(g);x,y,w,h=bbox(g);group=E.SubElement(root,'g',{'id':g['id'],'data-semantic-ref':g.get('semantic_ref','')})
        attrs={'fill':s['fill'],'stroke':s['stroke'],'stroke-width':str(s['stroke_width'])}
        if s['dashed']:attrs['stroke-dasharray']='5 4'
        shape=g.get('shape','rect')
        if shape in ('rect','rounded_rect'):E.SubElement(group,'rect',dict(attrs,x=str(x),y=str(y),width=str(w),height=str(h),**({'rx':str(g.get('corner_radius',8))} if shape=='rounded_rect' else {})))
        elif shape=='ellipse':E.SubElement(group,'ellipse',dict(attrs,cx=str(x+w/2),cy=str(y+h/2),rx=str(w/2),ry=str(h/2)))
        elif shape=='diamond':E.SubElement(group,'polygon',dict(attrs,points=f'{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}'))
        lines=g.get('label_lines',[g.get('label','')]);fs=s['font_size'];tx=g.get('text_x',x+w/2);ty=g.get('text_y',y+h/2-(len(lines)-1)*fs*.6)
        t=E.SubElement(group,'text',{'x':str(tx),'y':str(ty),'text-anchor':g.get('text_anchor','middle'),'dominant-baseline':'middle','font-size':str(fs),'font-family':s['font_family'],'fill':s['text_color']})
        for i,line in enumerate(lines):E.SubElement(t,'tspan',{'x':str(tx),'dy':'0' if i==0 else str(fs*1.2)}).text=str(line)
    for g in v.get('glyphs',[]):
        if g.get('role')=='container':draw_g(g)
    for p in v.get('paths',[]):
        s=style(p);attrs={'id':p['id'],'data-semantic-ref':p['semantic_ref'],'points':' '.join(f'{x},{y}' for x,y in p['points']),'fill':'none','stroke':s['stroke'],'stroke-width':str(s['stroke_width'])}
        if s['dashed']:attrs['stroke-dasharray']='5 4'
        if p.get('arrow','end')!='none':
            marker_id='arrow-'+p['id'];m=E.SubElement(defs,'marker',{'id':marker_id,'viewBox':'0 0 10 10','refX':'9','refY':'5','markerWidth':'7','markerHeight':'7','orient':'auto-start-reverse'});E.SubElement(m,'path',{'d':'M 0 0 L 10 5 L 0 10 z','fill':s['stroke']});attrs['marker-end']=f'url(#{marker_id})'
            if p.get('arrow')=='both':attrs['marker-start']=f'url(#{marker_id})'
        E.SubElement(root,'polyline',attrs)
        if p.get('label'):
            x,y=p['label_position'];E.SubElement(root,'text',{'x':str(x),'y':str(y),'font-size':str(s['font_size']),'font-family':s['font_family'],'fill':s['text_color'],'text-anchor':'middle'}).text=p['label']
    for g in v.get('glyphs',[]):
        if g.get('role')!='container':draw_g(g)
    return root

def drawio(doc):
    root=E.Element('mxfile',{'host':'app.diagrams.net','agent':'technical-diagram-options','version':'24.0.0'})
    for v in doc['views']:
        page=E.SubElement(root,'diagram',{'id':v['id'],'name':v.get('title',v['id'])});model=E.SubElement(page,'mxGraphModel',{'dx':str(v['canvas']['width']),'dy':str(v['canvas']['height']),'page':'1','pageWidth':str(v['canvas']['width']),'pageHeight':str(v['canvas']['height'])});r=E.SubElement(model,'root');E.SubElement(r,'mxCell',{'id':'0'});E.SubElement(r,'mxCell',{'id':'1','parent':'0'});gby={g['id']:g for g in v['glyphs']}
        for g in v['glyphs']:
            s=style(g);shape=g.get('shape','rect');shape_style={'rect':'rounded=0','rounded_rect':'rounded=1','ellipse':'ellipse','diamond':'rhombus','text':'text;strokeColor=none;fillColor=none'}[shape]
            st=f"{shape_style};html=0;whiteSpace=wrap;fillColor={s['fill']};strokeColor={s['stroke']};strokeWidth={s['stroke_width']};fontSize={s['font_size']};fontFamily={s['font_family']};fontColor={s['text_color']};dashed={int(s['dashed'])};"
            if shape=='text':st+='strokeColor=none;fillColor=none;'
            cell=E.SubElement(r,'mxCell',{'id':g['id'],'value':'\n'.join(g.get('label_lines',[g.get('label','')])),'style':st,'vertex':'1','parent':'1','semanticRef':g.get('semantic_ref','')});E.SubElement(cell,'mxGeometry',dict(zip(('x','y','width','height'),map(str,bbox(g)))),**{'as':'geometry'})
        for p in v.get('paths',[]):
            s=style(p);a=gby[p['source_instance']];b=gby[p['target_instance']];q=p['points'][0];z=p['points'][-1]
            st=f"edgeStyle=none;noEdgeStyle=1;html=0;rounded=0;endArrow={'none' if p.get('arrow','end')=='none' else 'block'};startArrow={'block' if p.get('arrow')=='both' else 'none'};strokeColor={s['stroke']};strokeWidth={s['stroke_width']};dashed={int(s['dashed'])};fontSize={s['font_size']};fontColor={s['text_color']};exitX={(q[0]-a['x'])/a['w']};exitY={(q[1]-a['y'])/a['h']};exitPerimeter=0;entryX={(z[0]-b['x'])/b['w']};entryY={(z[1]-b['y'])/b['h']};entryPerimeter=0;"
            cell=E.SubElement(r,'mxCell',{'id':p['id'],'value':'','style':st,'edge':'1','parent':'1','source':p['source_instance'],'target':p['target_instance'],'semanticRef':p['semantic_ref']});geo=E.SubElement(cell,'mxGeometry',{'relative':'1','as':'geometry'});points=E.SubElement(geo,'Array',{'as':'points'})
            for x,y in p['points'][1:-1]:E.SubElement(points,'mxPoint',{'x':str(x),'y':str(y)})
            if p.get('label'):
                # Independent native text glyph preserves explicit authored label placement.
                x,y=p['label_position'];cell=E.SubElement(r,'mxCell',{'id':p['id']+'-label','value':p['label'],'style':f'text;html=0;strokeColor=none;fillColor=none;fontSize={s["font_size"]};fontColor={s["text_color"]};','vertex':'1','parent':'1'});E.SubElement(cell,'mxGeometry',{'x':str(x-100),'y':str(y-s['font_size']),'width':'200','height':str(s['font_size']*1.5),'as':'geometry'})
    return root

def render(doc,out):
    result=check(doc)
    if not result['valid']:raise ValueError(json.dumps(result,ensure_ascii=False))
    out=Path(out);out.mkdir(parents=True,exist_ok=True);files=[]
    for v in doc['views']:
        name=out/(v['id']+'.svg');E.ElementTree(svg_view(v,doc)).write(name,encoding='utf-8',xml_declaration=True);files.append(str(name))
    name=out/(doc['diagram_id']+'.drawio');E.ElementTree(drawio(doc)).write(name,encoding='utf-8',xml_declaration=True);files.append(str(name))
    name=out/(doc['diagram_id']+'.source.json');name.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n');files.append(str(name))
    (out/'structural-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return files

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['check','render']);p.add_argument('input',type=Path);p.add_argument('--out-dir',type=Path,default=Path('output'));a=p.parse_args();doc=json.loads(a.input.read_text())
    if a.command=='check':r=check(doc);print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['valid'] else 1)
    print(json.dumps({'files':render(doc,a.out_dir),'visual_qa':'not performed by this script'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
