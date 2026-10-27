#!/usr/bin/env python3
import argparse,html
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--svg',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    svg=a.svg.read_text();a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(a.svg.stem)+'</title><style>body{margin:0;background:#eef0f2;display:grid;place-items:center;min-height:100vh}.slide{width:min(100vw,1280px);aspect-ratio:16/9;background:white}.slide>svg{width:100%;height:100%;display:block}</style><section class="slide" aria-label="技术机制图">'+svg+'</section></html>')
    print(a.out)
