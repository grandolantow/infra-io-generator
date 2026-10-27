#!/usr/bin/env python3
"""Render a source-backed diagram specification to editable SVG.

No network calls or model are required. The renderer preserves declared nodes and
edges; it does not verify the scientific claims. All automatic findings are
geometry diagnostics, not a declaration of diagram quality.
"""
from __future__ import annotations
import argparse
import hashlib
import heapq
import html
import json
import math
import re
import subprocess
from pathlib import Path

W, H = 1600, 900
STYLES = {
    "paper": dict(bg="#ffffff", ink="#172b3a", muted="#566674", line="#617584", panel="#f6f9fb", border="#ccd9e0", accent="#257c9a", fills=["#e5f1f5", "#eaf3e9", "#fff1dc", "#eeedf8"], rx=7, stroke=1.7),
    "mono": dict(bg="#ffffff", ink="#191919", muted="#555555", line="#414141", panel="#fafafa", border="#b6b6b6", accent="#111111", fills=["#f1f1f1", "#ffffff", "#e5e5e5", "#f8f8f8"], rx=0, stroke=1.7),
    "functional": dict(bg="#ffffff", ink="#192939", muted="#586877", line="#5c7185", panel="#fbfcfd", border="#c9d6df", accent="#326caa", fills=["#deedfc", "#e3f3e4", "#fff0cf", "#f0e4fa"], rx=8, stroke=1.8),
    "editorial": dict(bg="#fffdf7", ink="#292b30", muted="#626361", line="#707270", panel="#f5f1e9", border="#cfc8bb", accent="#a34f37", fills=["#eee6d8", "#dfe9e4", "#f3e2d4", "#e6e4ed"], rx=0, stroke=1.5),
    "blueprint": dict(bg="#f6faff", ink="#14395d", muted="#4d6d89", line="#4a7fa5", panel="#edf4fc", border="#b9d0e5", accent="#176ca4", fills=["#e5f0fc", "#edf5fd", "#d9eafa", "#f6faff"], rx=2, stroke=1.5),
    "dark": dict(bg="#101b2a", ink="#eef5fc", muted="#a4b7c9", line="#91abc1", panel="#17273b", border="#38516b", accent="#73cadb", fills=["#213e57", "#284638", "#51452c", "#3c3557"], rx=7, stroke=1.7),
}


def esc(s):
    return html.escape(str(s), quote=True)


def units(s):
    return sum(1 if ord(c) > 255 else (0.35 if c in " .,:;ilI'" else 0.57) for c in str(s))


def wrap(s, width, size, max_lines=None):
    """CJK-aware conservative wrapping; SVG still contains editable text."""
    result = []
    for para in str(s).split("\n"):
        line = ""
        for tok in re.findall(r"[A-Za-z0-9_./+×−=<>-]+\s*|[^A-Za-z0-9_./+×−=<>-]", para):
            if line and units(line + tok) * size > width:
                result.append(line.strip()); line = ""
            if units(tok) * size > width:
                for c in tok:
                    if line and units(line + c) * size > width:
                        result.append(line.strip()); line = ""
                    line += c
            else:
                line += tok
        if line.strip() or not result:
            result.append(line.strip())
    return result


def cyclic_edges(nodes, edges):
    adj = {n["id"]: [] for n in nodes}
    for i, e in enumerate(edges):
        if e["from"] in adj and e["to"] in adj:
            adj[e["from"]].append((e["to"], i))
    state, back = {}, set()
    def visit(u):
        state[u] = 1
        for v, i in adj[u]:
            if state.get(v) == 1:
                back.add(i)
            elif not state.get(v):
                visit(v)
        state[u] = 2
    for n in nodes:
        if not state.get(n["id"]): visit(n["id"])
    return back


def ranks_for(nodes, edges):
    # A state update belongs to the next step. It must never position the old
    # state downstream of the update within the current-step computation.
    temporal={i for i,e in enumerate(edges) if e.get("kind") in ("state_update","feedback")}
    dag_edges=[e for i,e in enumerate(edges) if i not in temporal]
    cycle_local=cyclic_edges(nodes,dag_edges)
    original_indices=[i for i in range(len(edges)) if i not in temporal]
    back=temporal|{original_indices[i] for i in cycle_local}
    ranks = {n["id"]: 0 for n in nodes}
    # Relax the DAG obtained by explicitly classifying feedback edges.
    for _ in nodes:
        changed = False
        for i, e in enumerate(edges):
            a, b = e["from"], e["to"]
            if i not in back and a in ranks and b in ranks and ranks[b] < ranks[a] + 1:
                ranks[b] = ranks[a] + 1; changed = True
        if not changed: break
    return ranks, back


def graph_positions(graph, box, config, horizontal=False):
    x, y, width, height = box
    nodes, edges = graph.get("nodes", []), graph.get("edges", [])
    ranks, back = ranks_for(nodes, edges)
    groups = {}
    for n in nodes:
        groups.setdefault(ranks[n["id"]], []).append(n)
    keys = sorted(groups)
    count = max(len(keys), 1)
    positions = {}
    label_size = config.get("label_size", 22)
    detail_size = config.get("detail_size",18)
    show_details=config.get("show_details",True)
    def desired_height(n,nw):
        label_lines=wrap(n.get("label",n["id"]),nw-28,label_size)
        detail_lines=wrap(n.get("detail",""),nw-28,detail_size) if show_details and n.get("detail") else []
        return max(62,len(label_lines)*label_size*1.28+len(detail_lines)*detail_size*1.23+(6 if detail_lines else 0)+18)
    if horizontal:
        columns = min(config.get("horizontal_columns", count), count)
        bands = math.ceil(count / columns)
        node_w = min(config.get("horizontal_node_width",260), max(105, (width - 26 * (columns - 1)) / columns))
        step = width / columns
        for j, rank in enumerate(keys):
            group = groups[rank]
            band = j // columns
            col = j % columns if band % 2 == 0 else columns - 1 - (j % columns)
            for k, n in enumerate(group):
                nw = node_w
                nh = desired_height(n,nw)
                cx = x + step * (col + .5)
                group_heights=[desired_height(z,nw) for z in group]
                available=height/bands
                free=available-sum(group_heights)
                gap=min(40,max(8,free/max(1,len(group)-1))) if len(group)>1 else 0
                block_h=sum(group_heights)+gap*(len(group)-1)
                sy=y+band*available+(available-block_h)/2
                cy=sy+sum(group_heights[:k])+gap*k+nh/2
                positions[n["id"]] = [round(cx - nw / 2, 2), round(cy - nh / 2, 2), round(nw, 2), round(nh, 2)]
    else:
        row_count=min(count,config.get("vertical_max_ranks",4)) if width>=650 else count
        col_count=math.ceil(count/row_count)
        # Variable-height ranks preserve all detail text. The renderer never
        # clips a node's height to a uniform slot merely to fit the page.
        rank_max_heights={}
        for j,rank in enumerate(keys):
            group=groups[rank]
            slot=width/col_count/len(group)
            nw=max(115,min(config.get("max_node_width",300),slot-42))
            rank_max_heights[rank]=max(desired_height(n,nw) for n in group)
        col_rank_keys={col:[rank for j,rank in enumerate(keys) if j//row_count==col] for col in range(col_count)}
        col_rank_keys={col:(list(reversed(ks)) if col%2 else ks) for col,ks in col_rank_keys.items()}
        rank_centers={}
        for col,ks in col_rank_keys.items():
            total=sum(rank_max_heights[r] for r in ks)
            gap=min(48,max(6,(height-total)/max(1,len(ks)-1))) if len(ks)>1 else 0
            sy=y+(height-total-gap*(len(ks)-1))/2
            for rank in ks:
                rank_centers[rank]=sy+rank_max_heights[rank]/2
                sy+=rank_max_heights[rank]+gap
        for j, rank in enumerate(keys):
            group = groups[rank]
            col=j//row_count;row=j%row_count
            if col%2:row=row_count-1-row
            slot = width / col_count / len(group)
            nw = min(config.get("max_node_width", 300), slot - 42)
            nw = max(115, nw)
            for k, n in enumerate(group):
                requested_h = desired_height(n,nw)
                nh = requested_h
                cx = x + col*width/col_count + slot * (k + .5)
                cy = rank_centers[rank]
                positions[n["id"]] = [round(cx - nw / 2, 2), round(cy - nh / 2, 2), round(nw, 2), round(nh, 2)]
    return positions, ranks, back


def rect_intersection(a, b, pad=0):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    return ax + aw + pad > bx and bx + bw + pad > ax and ay + ah + pad > by and by + bh + pad > ay


def visual_semantic_class(node):
    explicit=node.get("semantic_type",node.get("kind",""))
    if explicit in ("tensor","operation","state","control"):return explicit
    label=node.get("label","")
    if any(s in label for s in ("状态","记忆","写回新")):return "state"
    if any(s in label for s in ("事件","队列","scheduler","分派","阈值")):return "control"
    if any(s in label for s in ("输入","输出","表示","特征","query"," K / V","候选集合")):return "tensor"
    return "operation"


def segment_rect(p, q, box, pad=3):
    x,y,w,h = box; x -= pad; y -= pad; w += pad*2; h += pad*2
    if p[0] == q[0]:
        return x < p[0] < x+w and max(min(p[1],q[1]), y) < min(max(p[1],q[1]),y+h)
    if p[1] == q[1]:
        return y < p[1] < y+h and max(min(p[0],q[0]),x) < min(max(p[0],q[0]),x+w)
    return False


class SVG:
    def __init__(self, style):
        self.p = STYLES[style]; self.parts=[]; self.text_boxes=[]
    def add(self,s): self.parts.append(s)
    def text(self, text, x, y, size=22, color=None, weight=400, anchor="middle", width=500, key="", line_height=None):
        lines = wrap(text, width, size)
        lh = line_height or size*1.28
        color=color or self.p["ink"]
        self.add(f'<text id="{esc(key)}" x="{x:.2f}" y="{y:.2f}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" font-family="Microsoft YaHei, Noto Sans SC, Noto Sans CJK SC, sans-serif">')
        for i,line in enumerate(lines):
            self.add(f'<tspan x="{x:.2f}" dy="{0 if i==0 else lh:.2f}">{esc(line)}</tspan>')
        self.add('</text>')
        widest=max([units(t)*size for t in lines] or [0])
        bx=x-widest/2 if anchor=="middle" else x if anchor=="start" else x-widest
        self.text_boxes.append(dict(id=key,text=text,bbox=[bx,y-size*.9,widest,len(lines)*lh],estimate=True,size=size))
        return lines


def edge_points(a,b,all_boxes,key_a,key_b,index,feedback=False, side="right"):
    ax,ay,aw,ah=a; bx,by,bw,bh=b
    ac=(ax+aw/2,ay+ah/2); bc=(bx+bw/2,by+bh/2)
    if feedback or by < ay-5:
        lane=max(ax+aw,bx+bw)+38+(index%4)*13
        return [(ax+aw,ay+ah/2),(lane,ay+ah/2),(lane,by+bh/2),(bx+bw,by+bh/2)],"feedback"
    if abs(ac[1]-bc[1]) < min(ah,bh)*.55:
        if ac[0] < bc[0]:
            return [(ax+aw,ac[1]),(bx,bc[1])],"horizontal"
        return [(ax,ac[1]),(bx+bw,bc[1])],"horizontal"
    p=(ac[0],ay+ah); q=(bc[0],by)
    if abs(p[0]-q[0])<1:
        # Avoid unrelated blocks along a long vertical connection.
        blocked=any(segment_rect(p,q,r) for k,r in all_boxes.items() if k not in (key_a,key_b))
        if not blocked: return [p,q],"vertical"
        lane=max(r[0]+r[2] for r in all_boxes.values())+24+(index%4)*11
        return [(ax+aw,ac[1]),(lane,ac[1]),(lane,bc[1]),(bx+bw,bc[1])],"bypass"
    mid=(p[1]+q[1])/2
    # Long edges travel outside the graph, rather than through intermediate ranks.
    if by-(ay+ah)>max(ah,bh)*1.6:
        if ac[0] <= bc[0]:
            lane=min(r[0] for r in all_boxes.values())-24-(index%4)*10
            return [(ax,ac[1]),(lane,ac[1]),(lane,bc[1]),(bx,bc[1])],"bypass"
        lane=max(r[0]+r[2] for r in all_boxes.values())+24+(index%4)*10
        return [(ax+aw,ac[1]),(lane,ac[1]),(lane,bc[1]),(bx+bw,bc[1])],"bypass"
    return [p,(p[0],mid),(q[0],mid),q],"orthogonal"


def obstacle_route(a,b,all_boxes,key_a,key_b,index,feedback=False,used_segments=None,routing_box=None):
    """Route a declared edge with orthogonal A* around real node rectangles.

    This changes geometry only; no dependency is added or removed. Points lie on
    obstacle boundaries plus a small corridor grid, keeping complexity bounded.
    """
    ax,ay,aw,ah=a; bx,by,bw,bh=b
    ac=(ax+aw/2,ay+ah/2);bc=(bx+bw/2,by+bh/2)
    d=8
    offset=((index%3)-1)*7
    if feedback:
        start=(ax+aw,ac[1]+offset);lead=(ax+aw+d,ac[1]+offset)
        end=(bx+bw,bc[1]-offset);tail=(bx+bw+d,bc[1]-offset)
    elif abs(bc[0]-ac[0]) > abs(bc[1]-ac[1])*.95:
        if bc[0] > ac[0]:
            start=(ax+aw,ac[1]+offset);lead=(ax+aw+d,ac[1]+offset)
            end=(bx,bc[1]-offset);tail=(bx-d,bc[1]-offset)
        else:
            start=(ax,ac[1]+offset);lead=(ax-d,ac[1]+offset)
            end=(bx+bw,bc[1]-offset);tail=(bx+bw+d,bc[1]-offset)
    elif bc[1] >= ac[1] and by-(ay+ah)<18:
        start=(ax+aw,ac[1]+offset);lead=(ax+aw+d,ac[1]+offset)
        end=(bx+bw,bc[1]-offset);tail=(bx+bw+d,bc[1]-offset)
    elif bc[1] >= ac[1]:
        start=(ac[0]+offset,ay+ah);lead=(ac[0]+offset,ay+ah+d)
        end=(bc[0]-offset,by);tail=(bc[0]-offset,by-d)
    else:
        start=(ac[0]+offset,ay);lead=(ac[0]+offset,ay-d)
        end=(bc[0]-offset,by+bh);tail=(bc[0]-offset,by+bh+d)
    if key_a==key_b:
        lane=ax+aw+24
        return [(ax+aw,ay+ah*.35),(lane,ay+ah*.35),(lane,ay+ah*.75),(ax+aw,ay+ah*.75)],"explicit_self_loop"
    if routing_box:
        rx,ry,rw,rh=routing_box
        minx,maxx=max(35,rx-32),min(1565,rx+rw+32)
        miny,maxy=max(205,ry-22),min(800,ry+rh+22)
    else:minx,maxx,miny,maxy=35,1565,205,800
    xs={minx,maxx,lead[0],tail[0]};ys={miny,maxy,lead[1],tail[1]}
    for r in all_boxes.values():
        x,y,w,h=r
        xs.update((max(minx,x-18),x+w/2,min(maxx,x+w+18)))
        ys.update((max(miny,y-18),y+h/2,min(maxy,y+h+18)))
    xs=sorted(round(v,2) for v in xs if minx<=v<=maxx)
    ys=sorted(round(v,2) for v in ys if miny<=v<=maxy)
    lead=(round(lead[0],2),round(lead[1],2));tail=(round(tail[0],2),round(tail[1],2))
    if lead[0] not in xs or lead[1] not in ys or tail[0] not in xs or tail[1] not in ys:
        return edge_points(a,b,all_boxes,key_a,key_b,index,feedback)
    si=(xs.index(lead[0]),ys.index(lead[1]));ti=(xs.index(tail[0]),ys.index(tail[1]))
    blocked_cache={}
    def blocked(p,q):
        key=(p,q) if p<q else (q,p)
        if key not in blocked_cache:
            blocked_cache[key]=any(segment_rect(p,q,r,5) for r in all_boxes.values())
        return blocked_cache[key]
    queue=[];initial=(si[0],si[1],-1)
    heapq.heappush(queue,(0,0,initial));costs={initial:0};previous={}
    best=None
    while queue:
        _,cost,state=heapq.heappop(queue)
        ix,iy,direction=state
        if cost!=costs.get(state):continue
        if (ix,iy)==ti:best=state;break
        p=(xs[ix],ys[iy])
        for nx,ny,nd in ((ix-1,iy,0),(ix+1,iy,0),(ix,iy-1,1),(ix,iy+1,1)):
            if nx<0 or ny<0 or nx>=len(xs) or ny>=len(ys):continue
            q=(xs[nx],ys[ny])
            if blocked(p,q):continue
            dist=abs(p[0]-q[0])+abs(p[1]-q[1])
            penalty=20 if direction not in (-1,nd) else 0
            # Discourage sharing a corridor with a previously rendered edge.
            for u,v in used_segments or []:
                if p[0]==q[0]==u[0]==v[0] and max(min(p[1],q[1]),min(u[1],v[1]))<min(max(p[1],q[1]),max(u[1],v[1])):penalty+=dist*.3
                if p[1]==q[1]==u[1]==v[1] and max(min(p[0],q[0]),min(u[0],v[0]))<min(max(p[0],q[0]),max(u[0],v[0])):penalty+=dist*.3
            nc=cost+dist+penalty;ns=(nx,ny,nd)
            if nc<costs.get(ns,float("inf")):
                costs[ns]=nc;previous[ns]=state
                heuristic=abs(q[0]-tail[0])+abs(q[1]-tail[1])
                heapq.heappush(queue,(nc+heuristic,nc,ns))
    if best is None:
        pts,route=edge_points(a,b,all_boxes,key_a,key_b,index,feedback)
        return pts,"fallback_"+route
    path=[]
    while best!=initial:
        path.append((xs[best[0]],ys[best[1]]));best=previous[best]
    path.append(lead);path.reverse()
    pts=[start]+path+[end]
    compact=[]
    for p in pts:
        if compact and p==compact[-1]:continue
        if len(compact)>=2 and ((compact[-2][0]==compact[-1][0]==p[0]) or (compact[-2][1]==compact[-1][1]==p[1])):compact[-1]=p
        else:compact.append(p)
    return compact,"obstacle_aware_feedback" if feedback else "obstacle_aware"


def draw_graph(svg, graph, box, scenario, style, config, horizontal=False):
    p=svg.p; pos,ranks,back=graph_positions(graph,box,config,horizontal)
    overrides=config.get("positions",{}).get(scenario,{})
    for key,val in overrides.items():
        if key in pos: pos[key]=val
    nodes={n["id"]:n for n in graph.get("nodes",[])}
    edge_records=[]; label_size=config.get("label_size",22);detail_size=config.get("detail_size",18);used_segments=[]
    svg.add(f'<g id="{scenario}" data-scenario="{scenario}">')
    for i,e in enumerate(graph.get("edges",[])):
        a,b=e["from"],e["to"]
        if a not in pos or b not in pos: continue
        pts,route=obstacle_route(pos[a],pos[b],pos,a,b,i,i in back,used_segments,box)
        used_segments.extend(zip(pts,pts[1:]))
        eid=f'{scenario}-edge-{e.get("id",str(i+1))}'
        kind=e.get("kind","data")
        dashed=' stroke-dasharray="7 5"' if kind in ("control","state","state_update","state_read","feedback","residual") else ''
        stroke=p["accent"] if kind in ("control","state","state_update","state_read","feedback") else p["line"]
        d="M "+" L ".join(f'{x:.2f},{y:.2f}' for x,y in pts)
        factrefs=e.get("fact_refs",e.get("facts",[]))
        svg.add(f'<path id="{esc(eid)}" data-from="{esc(a)}" data-to="{esc(b)}" data-kind="{esc(kind)}" data-fact="{esc(" ".join(factrefs))}" d="{d}" fill="none" stroke="{stroke}" stroke-width="{p["stroke"]+0.3}"{dashed} marker-end="url(#arrow)"/>')
        edge_records.append(dict(id=eid,from_id=a,to_id=b,kind=kind,points=pts,route=route,label=e.get("label","")))
    # Nodes cover lines only where their declared endpoints meet the boundary.
    for j,(nid,n) in enumerate(nodes.items()):
        x,y,w,h=pos[nid]
        semantic_class=visual_semantic_class(n)
        fill=p["fills"][{"tensor":0,"operation":1,"state":2,"control":3}[semantic_class]]
        if scenario=="baseline" and style not in ("dark","functional"): fill=p["panel"]
        factrefs=n.get("fact_refs",n.get("facts",[]))
        svg.add(f'<g id="{esc(scenario+"-node-"+nid)}" data-node="{esc(nid)}" data-semantic-class="{semantic_class}" data-fact="{esc(" ".join(factrefs))}" data-rank="{ranks[nid]}">')
        svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{p["rx"]}" fill="{fill}" stroke="{p["border"]}" stroke-width="{p["stroke"]}"/>')
        lines=wrap(n.get("label",nid),w-28,label_size)
        detail_lines=wrap(n.get("detail",""),w-28,detail_size) if config.get("show_details",True) and n.get("detail") else []
        total=len(lines)*label_size*1.28+len(detail_lines)*detail_size*1.23+(6 if detail_lines else 0)
        ty=y+h/2-total/2+label_size*.95
        svg.text(n.get("label",nid),x+w/2,ty,label_size,width=w-28,key=scenario+"-label-"+nid,weight=500)
        if detail_lines:
            dy=ty+len(lines)*label_size*1.28+4
            svg.text(n["detail"],x+w/2,dy,detail_size,color=p["muted"],width=w-28,key=scenario+"-detail-"+nid,line_height=detail_size*1.23)
        svg.add('</g>')
    # Place edge labels in actual free space, preserving their association with
    # an edge segment. This is independent of the semantic edge routing.
    label_rects=[]
    for i,e in enumerate(edge_records):
        if not e["label"]: continue
        pts=e["points"]
        segments=list(zip(pts,pts[1:]))
        label=e["label"]
        sz=config.get("edge_label_size",18)
        # A narrow multiline callout fits the genuine side corridors around
        # nodes; a long single-line edge label often cannot fit those corridors.
        width=min(config.get("edge_label_max_width",86),max(64,units(label)*sz+4))
        lines=wrap(label,width,sz)
        actual_width=max(units(t)*sz for t in lines)*1.10+14
        lh=len(lines)*sz*1.28+8
        choices=[]
        for j,(a,b) in enumerate(segments):
            seglen=abs(a[0]-b[0])+abs(a[1]-b[1])
            for frac in (.5,.25,.75):
                mx=a[0]+(b[0]-a[0])*frac;my=a[1]+(b[1]-a[1])*frac
                if a[0]==b[0]:
                    options=[(mx+off,my-lh/2) for off in (10,30,55)]+[(mx-actual_width-off,my-lh/2) for off in (10,30,55)]
                else:
                    options=[(mx-actual_width/2,my-lh-off) for off in (7,27,52)]+[(mx-actual_width/2,my+off) for off in (7,27,52)]
                for option_index,(tx,ty) in enumerate(options):
                    r=[tx,ty,actual_width,lh]
                    collisions=sum(rect_intersection(r,z,8) for z in pos.values())+sum(rect_intersection(r,z,6) for z in label_rects)
                    region_left=max(50,box[0]-43);region_right=min(1550,box[0]+box[2]+43)
                    region_top=max(205,box[1]-24);region_bottom=min(800,box[1]+box[3]+24)
                    outside=tx<region_left or tx+actual_width>region_right or ty<region_top or ty+lh>region_bottom
                    score=collisions*10000+outside*100000+max(0,actual_width-seglen)*.5+j*2+(0 if frac==.5 else 3)+option_index*.5
                    choices.append((score,r))
        score,r=min(choices,key=lambda q:q[0])
        leader=None
        if score>=10000:
            # Search a nearby empty patch and retain a visible annotation leader
            # to the exact data/control edge. The leader has no arrowhead and is
            # explicitly marked as annotation, not another semantic connection.
            left=max(50,box[0]-43);right=min(1550,box[0]+box[2]+43)
            top=max(205,box[1]-24);bottom=min(800,box[1]+box[3]+24)
            globals=[]
            for tx0 in range(int(left),int(right-actual_width)+1,18):
                for ty0 in range(int(top),int(bottom-lh)+1,18):
                    rr=[tx0,ty0,actual_width,lh]
                    if any(rect_intersection(rr,z,7) for z in pos.values()) or any(rect_intersection(rr,z,6) for z in label_rects):continue
                    center=(tx0+actual_width/2,ty0+lh/2)
                    closest=[]
                    for a,b in segments:
                        if a[0]==b[0]:projected=(a[0],min(max(center[1],min(a[1],b[1])),max(a[1],b[1])))
                        else:projected=(min(max(center[0],min(a[0],b[0])),max(a[0],b[0])),a[1])
                        anchors=[projected]+[(a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f) for f in (.25,.5,.75)]
                        for q in anchors:
                            distance=abs(q[0]-center[0])+abs(q[1]-center[1])
                            if distance>520:continue
                            for bend in [(q[0],center[1]),(center[0],q[1])]:
                                route=[center,bend,q]
                                if not any(segment_rect(u,v,z,4) for u,v in zip(route,route[1:]) for z in pos.values()):
                                    closest.append((distance,route))
                    if closest:
                        distance,route=min(closest,key=lambda q:q[0])
                        globals.append((distance,rr,route))
            if globals:
                _,r,leader=min(globals,key=lambda q:q[0]);score=0
        tx,ty,rw,rh=r
        label_rects.append(r);e["label_bbox"]=r;e["label_placement_collisions"]=int(score//10000)
        if leader:
            ld="M "+" L ".join(f'{x:.2f},{y:.2f}' for x,y in leader)
            svg.add(f'<path d="{ld}" fill="none" stroke="{p["muted"]}" stroke-width="1" stroke-dasharray="2 3" data-link-kind="annotation"/>')
            e["label_leader"]=leader
        svg.add(f'<rect x="{tx-3:.2f}" y="{ty-2:.2f}" width="{rw+6:.2f}" height="{rh+4:.2f}" fill="{p["bg"]}" opacity=".93"/>')
        svg.text(label,tx+4,ty+sz*.93,sz,color=p["muted"],anchor="start",width=width,key=e["id"]+"-label")
    svg.add('</g>')
    return dict(scenario=scenario,nodes=[dict(id=nid,bbox=pos[nid],rank=ranks[nid],label=n.get("label",nid),detail=n.get("detail",""),visual_semantic_class=visual_semantic_class(n)) for nid,n in nodes.items()],edges=edge_records,box=box,feedback_edge_indices=sorted(back))


def check_geometry(layout, texts):
    findings=[]
    for g in layout["graphs"]:
        boxes={n["id"]:n["bbox"] for n in g["nodes"]}
        ns=g["nodes"]
        for i,a in enumerate(ns):
            x,y,w,h=a["bbox"]
            if min(x,y)<0 or x+w>W or y+h>H:
                findings.append(dict(kind="node_out_of_canvas",severity="error",scenario=g["scenario"],element=a["id"]))
            for b in ns[i+1:]:
                if rect_intersection(a["bbox"],b["bbox"]):
                    findings.append(dict(kind="node_overlap",severity="error",scenario=g["scenario"],elements=[a["id"],b["id"]]))
        for e in g["edges"]:
            for nid,r in boxes.items():
                if nid in (e["from_id"],e["to_id"]):continue
                if any(segment_rect(a,b,r,1) for a,b in zip(e["points"],e["points"][1:])):
                    findings.append(dict(kind="edge_crosses_unrelated_node",severity="warning",scenario=g["scenario"],edge=e["id"],node=nid))
            if "label_bbox" in e:
                for nid,r in boxes.items():
                    if rect_intersection(e["label_bbox"],r,1):
                        findings.append(dict(kind="edge_label_overlaps_node",severity="warning",scenario=g["scenario"],edge=e["id"],node=nid))
        for n in ns:
            tid=g["scenario"]+"-label-"+n["id"]
            t=next((t for t in texts if t["id"]==tid),None)
            if t:
                x,y,w,h=n["bbox"]; tx,ty,tw,th=t["bbox"]
                if tx<x+5 or tx+tw>x+w-5 or ty<y-2 or ty+th>y+h+8:
                    findings.append(dict(kind="estimated_node_text_overflow",severity="warning",scenario=g["scenario"],element=n["id"],estimate=True,text_bbox=t["bbox"],node_bbox=n["bbox"]))
    for t in texts:
        x,y,w,h=t["bbox"]
        if x<0 or y<0 or x+w>W or y+h>H:
            findings.append(dict(kind="estimated_text_out_of_canvas",severity="warning",element=t["id"],estimate=True))
    return dict(status="geometry_checked_semantics_not_evaluated",findings=findings,error_count=sum(f["severity"]=="error" for f in findings),warning_count=sum(f["severity"]=="warning" for f in findings),text_measurement="conservative_character_width_estimate_not_browser_bbox",visual_review="not_run",semantic_review="not_run")


def quotient_graph(graph,config):
    groups=config.get("semantic_groups",[])
    if not groups:
        ranks,_=ranks_for(graph["nodes"],graph["edges"])
        maximum=max(ranks.values(),default=0)
        groups=[dict(id="input",label="输入与上下文",nodes=[n["id"] for n in graph["nodes"] if ranks[n["id"]]==0]),dict(id="core",label="关键机制",nodes=[n["id"] for n in graph["nodes"] if 0<ranks[n["id"]]<maximum]),dict(id="output",label="输出与后续状态",nodes=[n["id"] for n in graph["nodes"] if ranks[n["id"]]==maximum])]
    # Accept explicit task-local grouping but never silently discard a node.
    mapped={nid:g["id"] for g in groups for nid in g.get("nodes",[])}
    unmatched=[n["id"] for n in graph["nodes"] if n["id"] not in mapped]
    if unmatched:
        groups=groups+[dict(id="other",label="其他必要机制",nodes=unmatched)]
        mapped.update({nid:"other" for nid in unmatched})
    nodes=[dict(id=g["id"],label=g["label"],detail=f'{len(g.get("nodes",[]))} 个节点在右侧展开',member_nodes=g.get("nodes",[])) for g in groups if g.get("nodes")]
    edges=[];seen={}
    for i,e in enumerate(graph["edges"]):
        a,b=mapped.get(e["from"]),mapped.get(e["to"])
        if a and b and a!=b:
            k=(a,b,e.get("kind","data"))
            if k not in seen:
                seen[k]=dict(id="q"+str(len(seen)+1),**{"from":a,"to":b},kind=e.get("kind","data"),label="",source_edges=[])
            seen[k]["source_edges"].append(i)
    edges=list(seen.values())
    return dict(name="机制位置概览",nodes=nodes,edges=edges),groups


def render(spec,layout_name="compare",style="paper",round_number=1,config=None):
    cfg=dict(label_size=22,detail_size=18,edge_label_size=18,max_node_width=300,show_details=True)
    cfg.update(config or {})
    source_spec_hash=hashlib.sha256(json.dumps(spec,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if cfg.get("display_overrides"):
        spec=json.loads(json.dumps(spec))
        for scenario,mapping in cfg["display_overrides"].items():
            for node in spec.get(scenario,{}).get("nodes",[]):
                node.update(mapping.get(node["id"],{}))
    svg=SVG(style); p=svg.p
    svg.add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="diagram-title diagram-desc">')
    svg.add(f'<title id="diagram-title">{esc(spec["title"])}</title><desc id="diagram-desc">{esc(spec.get("subtitle",""))}</desc>')
    svg.add(f'<metadata>{esc(json.dumps(dict(task_id=spec["id"],round=round_number,layout=layout_name,style=style,source_url=spec.get("source_url"),facts=spec.get("facts",[])),ensure_ascii=False))}</metadata>')
    svg.add(f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{p["line"]}"/></marker></defs>')
    svg.add(f'<rect width="{W}" height="{H}" fill="{p["bg"]}"/>')
    svg.text(spec["title"],60,62,36,anchor="start",weight=650,width=1450,key="title")
    svg.text(spec.get("subtitle",""),60,108,24,color=p["muted"],anchor="start",width=1450,key="subtitle")
    svg.add(f'<line x1="60" y1="139" x2="1540" y2="139" stroke="{p["border"]}"/>')
    base=spec.get("baseline",{}); prop=spec.get("proposed",{})
    graphs=[]
    if layout_name=="compare":
        panels=[("baseline",base,(60,162,460,622)),("proposed",prop,(558,162,982,622))]
        for scenario,g,(x,y,w,h) in panels:
            svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{p["panel"]}" stroke="{p["border"]}"/>')
            svg.text(g.get("name",scenario),x+25,y+39,25,anchor="start",weight=600,width=w-50,key=scenario+"-heading")
            local_cfg={**cfg,"max_node_width":240} if scenario=="baseline" else cfg
            graphs.append(draw_graph(svg,g,(x+50,y+72,w-100,h-103),scenario,style,local_cfg))
    elif layout_name=="backbone":
        overview,overview_groups=quotient_graph(prop,cfg)
        svg.text("整体机制概览",60,188,23,anchor="start",color=p["muted"],key="context-heading")
        svg.text(prop.get("name","关键机制展开"),470,188,25,anchor="start",weight=600,width=1060,key="proposed-heading")
        svg.add(f'<rect x="449" y="207" width="1091" height="366" rx="8" fill="{p["panel"]}" stroke="{p["border"]}" stroke-dasharray="7 5"/>')
        overview_layout=draw_graph(svg,overview,(68,224,330,326),"overview",style,{**cfg,"label_size":20,"max_node_width":275,"vertical_max_ranks":4})
        overview_layout["semantic_groups"]=overview_groups
        graphs.append(overview_layout)
        graphs.append(draw_graph(svg,prop,(476,225,1036,330),"proposed",style,{**cfg,"label_size":20,"vertical_max_ranks":3,"max_node_width":305}))
        svg.add(f'<line x1="60" y1="591" x2="1540" y2="591" stroke="{p["border"]}"/>')
        svg.text(base.get("name","基线参照"),60,624,22,anchor="start",weight=600,width=1480,key="baseline-heading")
        graphs.append(draw_graph(svg,base,(75,646,1450,139),"baseline",style,{**cfg,"label_size":20,"horizontal_node_width":260},horizontal=True))
    elif layout_name=="mechanism":
        # Proposed mechanism has full width. Baseline context is a genuine graph,
        # not a prose replacement that drops its declared nodes or edges.
        svg.text(prop.get("name","关键机制"),60,190,27,anchor="start",weight=600,width=1460,key="proposed-heading")
        graphs.append(draw_graph(svg,prop,(75,220,1450,310),"proposed",style,{**cfg,"label_size":20},horizontal=True))
        svg.add(f'<line x1="60" y1="567" x2="1540" y2="567" stroke="{p["border"]}"/>')
        svg.text(base.get("name","基线参照"),60,601,23,anchor="start",weight=600,width=1450,key="baseline-heading")
        # A wide, shallower context view keeps all baseline facts present.
        graphs.append(draw_graph(svg,base,(75,627,1450,169),"baseline",style,{**cfg,"label_size":20},horizontal=True))
    else: raise ValueError("Unknown layout: "+layout_name)
    annotations=cfg.get("annotations",[])
    notes=spec.get("mechanism_notes",[])
    if annotations:
        note="；".join(annotations)
        svg.text(note,60,824,18,anchor="start",width=1480,key="contract-annotations",line_height=23)
    elif notes:
        note=notes[0] if isinstance(notes[0],str) else str(notes[0])
        svg.text(note,60,829,20,anchor="start",width=1480,key="mechanism-note")
    source=spec.get("source_url","")
    svg.text(source,60,879,16,color=p["muted"],anchor="start",width=1270,key="source")
    svg.text(f'R{round_number} · {layout_name} · {style}',1540,879,16,color=p["muted"],anchor="end",width=250,key="version")
    svg.add('</svg>')
    content="\n".join(svg.parts)
    layout=dict(task_id=spec["id"],canvas=dict(width=W,height=H),round=round_number,layout=layout_name,style=style,config=cfg,graphs=graphs,text_boxes=svg.text_boxes,fact_ids=[f.get("id") for f in spec.get("facts",[])],spec_sha256=source_spec_hash,display_overrides=cfg.get("display_overrides",{}))
    qa=check_geometry(layout,svg.text_boxes)
    semantic_graphs=[g for g in graphs if g["scenario"] in ("baseline","proposed")]
    qa.update(task_id=spec["id"],round=round_number,layout=layout_name,style=style,nodes_expected=sum(len(g.get("nodes",[])) for g in (base,prop)),nodes_rendered=sum(len(g["nodes"]) for g in semantic_graphs),edges_expected=sum(len(g.get("edges",[])) for g in (base,prop)),edges_rendered=sum(len(g["edges"]) for g in semantic_graphs),overview_is_quotient_graph=layout_name=="backbone")
    return content,layout,qa


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--round",type=int,choices=(1,2,3),default=1)
    ap.add_argument("--layout",choices=("compare","backbone","mechanism"),default="compare")
    ap.add_argument("--style",choices=tuple(STYLES),default="paper")
    ap.add_argument("--config",type=Path)
    ap.add_argument("--png",action="store_true",help="Run installed Inkscape to rasterize the SVG")
    args=ap.parse_args()
    spec=json.loads(args.spec.read_text())
    config=json.loads(args.config.read_text()) if args.config else {}
    content,layout,qa=render(spec,args.layout,args.style,args.round,config)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(content,encoding="utf-8")
    args.out.with_suffix(".layout.json").write_text(json.dumps(layout,ensure_ascii=False,indent=2))
    args.out.with_suffix(".qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    if args.png:
        png_path=args.out.with_suffix(".png")
        attempts=[]
        for attempt in range(1,4):
            result=subprocess.run(["inkscape",str(args.out),"--export-type=png","--export-filename="+str(png_path)],capture_output=True,text=True)
            item=dict(attempt=attempt,exit_code=result.returncode,stderr=result.stderr[-1200:])
            decoded=False
            if result.returncode==0 and png_path.exists():
                try:
                    from PIL import Image
                    with Image.open(png_path) as im:
                        im.load();size=list(im.size)
                    decoded=size==[W,H]
                    item.update(full_decode_passed=decoded,image_size=size,size_bytes=png_path.stat().st_size)
                except Exception as error:item.update(full_decode_passed=False,decode_error=str(error))
            attempts.append(item)
            if decoded:break
            if png_path.exists():
                failed_path=png_path.with_name(png_path.stem+f".failed-attempt-{attempt}.png")
                png_path.rename(failed_path);item["failed_artifact"]=str(failed_path)
        qa["png_render_exit_code"]=result.returncode
        qa["png_rendered"]=decoded
        qa["png_full_decode_passed"]=decoded
        qa["render_attempts"]=attempts
        if decoded:qa["png_sha256"]=hashlib.sha256(png_path.read_bytes()).hexdigest()
        else:qa["render_error"]=attempts[-1]
        args.out.with_suffix(".qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    print(json.dumps(dict(svg=str(args.out),nodes=qa["nodes_rendered"],edges=qa["edges_rendered"],errors=qa["error_count"],warnings=qa["warning_count"])))


if __name__=="__main__":main()
