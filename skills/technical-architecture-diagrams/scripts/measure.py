#!/usr/bin/env python3
"""Measure rendered SVG text with installed Inkscape and update QA records.

This is a real renderer bounding-box measurement, not a browser or PowerPoint
test. It checks geometry only and leaves semantic/visual judgments unreviewed.
"""
import argparse
import json
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET


def intersects(a,b,pad=0):
    x,y,w,h=a;u,v,s,t=b
    return x+w+pad>u and u+s+pad>x and y+h+pad>v and v+t+pad>y


def measure(svg_path):
    result=subprocess.run(["inkscape",str(svg_path),"--query-all"],capture_output=True,text=True)
    if result.returncode:
        return {"status":"failed","error":result.stderr[-1500:]}
    boxes={}
    for line in result.stdout.splitlines():
        fields=line.rsplit(",",4)
        if len(fields)!=5:continue
        try:boxes[fields[0]]=[float(v) for v in fields[1:]]
        except ValueError:continue
    layout_path=svg_path.with_suffix(".layout.json")
    qa_path=svg_path.with_suffix(".qa.json")
    if not layout_path.exists():
        return {"status":"measured","bbox_count":len(boxes),"boxes":boxes}
    root=ET.parse(svg_path).getroot()
    viewbox=root.get('viewBox','').replace(',', ' ').split()
    if len(viewbox)!=4:
        raise ValueError('SVG must declare a four-number viewBox for canvas checks')
    cx,cy,cw,ch=map(float,viewbox)
    layout=json.loads(layout_path.read_text());qa=json.loads(qa_path.read_text())
    qa["findings"]=[f for f in qa.get("findings",[]) if f["kind"] not in ("estimated_node_text_overflow","estimated_text_out_of_canvas","edge_label_overlaps_node","actual_node_text_overflow","actual_text_out_of_canvas","actual_edge_label_overlaps_node","actual_text_overlap")]
    texts=[t for t in layout.get("text_boxes",[]) if t["id"] in boxes]
    findings=[]
    for g in layout["graphs"]:
        for n in g["nodes"]:
            for tag in ("label","detail"):
                tid=g["scenario"]+"-"+tag+"-"+n["id"]
                if tid not in boxes:continue
                x,y,w,h=n["bbox"];tx,ty,tw,th=boxes[tid]
                if tx<x+3 or tx+tw>x+w-3 or ty<y+2 or ty+th>y+h-2:
                    findings.append(dict(kind="actual_node_text_overflow",severity="warning",scenario=g["scenario"],element=n["id"],text_kind=tag,text_bbox=boxes[tid],node_bbox=n["bbox"]))
        for e in g["edges"]:
            tid=e["id"]+"-label"
            if tid not in boxes:continue
            for n in g["nodes"]:
                if intersects(boxes[tid],n["bbox"],0):
                    findings.append(dict(kind="actual_edge_label_overlaps_node",severity="warning",scenario=g["scenario"],edge=e["id"],node=n["id"]))
    for i,t in enumerate(texts):
        a=boxes[t["id"]];x,y,w,h=a
        if x<cx or y<cy or x+w>cx+cw or y+h>cy+ch:
            findings.append(dict(kind="actual_text_out_of_canvas",severity="warning",element=t["id"],bbox=a))
        for u in texts[i+1:]:
            if intersects(a,boxes[u["id"]],0):
                findings.append(dict(kind="actual_text_overlap",severity="warning",elements=[t["id"],u["id"]]))
    qa["findings"].extend(findings)
    qa["error_count"]=sum(f.get("severity")=="error" for f in qa["findings"])
    qa["warning_count"]=sum(f.get("severity")=="warning" for f in qa["findings"])
    qa["text_measurement"]="inkscape_rendered_text_bbox"
    qa["measured_text_count"]=len(texts)
    qa["bbox_measurement_exit_code"]=result.returncode
    qa["bbox_measurement_scope"]="SVG/Inkscape only; not browser or PowerPoint; no semantic judgment"
    qa_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2))
    svg_path.with_suffix(".bboxes.json").write_text(json.dumps({"renderer":"Inkscape","boxes":boxes},ensure_ascii=False,indent=2))
    return {"svg":str(svg_path),"text_count":len(texts),"errors":qa["error_count"],"warnings":qa["warning_count"]}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths",nargs="+",type=Path)
    args=ap.parse_args()
    for p in args.paths:
        files=sorted(p.rglob("*.svg")) if p.is_dir() else [p]
        for f in files:print(json.dumps(measure(f),ensure_ascii=False))


if __name__=="__main__":main()
