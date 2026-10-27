#!/usr/bin/env python3
"""Legacy draft checker: exercise local SVG edits without changing the source fact files.

The probe moves one proposed module by 12 px through a layout override and
checks persistent node/edge IDs, unrelated module positions, native SVG text,
and the declared connections' attachment to the moved module. It is not a
PowerPoint editing test or a scientific correctness judgment.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
from xml.etree import ElementTree as ET


def on_boundary(point,box,eps=.1):
    x,y,w,h=box;px,py=point
    return (abs(px-x)<=eps or abs(px-x-w)<=eps) and y-eps<=py<=y+h+eps or (abs(py-y)<=eps or abs(py-y-h)<=eps) and x-eps<=px<=x+w+eps


def probe(spec,config,renderer):
    svg,before,qa=renderer.render(spec,"compare","paper",3,config)
    graph=next(g for g in before["graphs"] if g["scenario"]=="proposed")
    # Select a sink-like/rightmost module to make the visual edit representative
    # while leaving room for a modest displacement within the slide.
    target=max(graph["nodes"],key=lambda n:n["bbox"][0])
    nid=target["id"];box=list(target["bbox"]);box[0]-=12
    adjusted=copy.deepcopy(config)
    adjusted.setdefault("positions",{}).setdefault("proposed",{})[nid]=box
    svg_after,after,qa_after=renderer.render(spec,"compare","paper",3,adjusted)
    graph_after=next(g for g in after["graphs"] if g["scenario"]=="proposed")
    a_nodes={n["id"]:n["bbox"] for n in graph["nodes"]};b_nodes={n["id"]:n["bbox"] for n in graph_after["nodes"]}
    a_edges={(e["id"],e["from_id"],e["to_id"]) for e in graph["edges"]}
    b_edges={(e["id"],e["from_id"],e["to_id"]) for e in graph_after["edges"]}
    related=[e for e in graph_after["edges"] if nid in (e["from_id"],e["to_id"])]
    attachments=[]
    for e in related:
        point=e["points"][0] if e["from_id"]==nid else e["points"][-1]
        attachments.append(on_boundary(point,box))
    tree=ET.fromstring(svg_after);ns={"s":"http://www.w3.org/2000/svg"}
    record=dict(task_id=spec["id"],probe="move_one_module_12px_with_layout_override",moved_node=nid,source_fact_sha256_unchanged=before["spec_sha256"]==after["spec_sha256"],node_ids_preserved=set(a_nodes)==set(b_nodes),edge_ids_and_endpoints_preserved=a_edges==b_edges,unrelated_node_positions_unchanged=all(a_nodes[k]==b_nodes[k] for k in a_nodes if k!=nid),connected_edges_follow_moved_node=all(attachments),connected_edges_checked=len(attachments),native_text_count=len(tree.findall(".//s:text",ns)),raster_image_count=len(tree.findall(".//s:image",ns)),scope="SVG/source layout edit only; no PowerPoint object edit tested")
    record["passed"]=all(record[k] for k in ("source_fact_sha256_unchanged","node_ids_preserved","edge_ids_and_endpoints_preserved","unrelated_node_positions_unchanged","connected_edges_follow_moved_node")) and record["native_text_count"]>0 and record["raster_image_count"]==0
    return record


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    renderer_path=Path(__file__).with_name("render.py")
    sp=importlib.util.spec_from_file_location("renderer",renderer_path);renderer=importlib.util.module_from_spec(sp);sp.loader.exec_module(renderer)
    records=[]
    for p in sorted(args.root.glob("facts_[12]/*.json")):
        spec=json.loads(p.read_text())
        if "proposed" not in spec:continue
        config_path=args.root/"configs/r3"/(spec["id"]+".json")
        config=json.loads(config_path.read_text()) if config_path.exists() else {}
        records.append(probe(spec,config,renderer))
    result=dict(passed=sum(r["passed"] for r in records),total=len(records),records=records)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!="records"}))


if __name__=="__main__":main()
