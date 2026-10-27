#!/usr/bin/env python3
import argparse,json
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--query',default='');p.add_argument('--style',choices=['baseline','variant','all'],default='baseline');p.add_argument('--limit',type=int,default=5);a=p.parse_args()
    path=Path(__file__).resolve().parents[1]/'references/reference-index.json'
    data=json.loads(path.read_text())
    words=a.query.casefold().split()
    hits=[r for r in data if (a.style=='all' or r['style_class']==a.style) and all(w in json.dumps(r,ensure_ascii=False).casefold() for w in words)]
    print(json.dumps(hits[:max(1,min(a.limit,100))],ensure_ascii=False,indent=2))
