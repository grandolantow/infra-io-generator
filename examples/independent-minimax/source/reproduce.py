#!/usr/bin/env python3
"""Portable reproduction entry point; dependencies are supplied, never installed."""
from pathlib import Path
import argparse,os,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=ROOT/'source-input')
    p.add_argument('--out',type=Path,default=ROOT)
    p.add_argument('--chrome',default=os.environ.get('CHROME_BINARY'))
    p.add_argument('--playwright',default=os.environ.get('PLAYWRIGHT_MODULE'))
    p.add_argument('--graph-js',type=Path,default=ROOT/'runtime/app.min.js')
    p.add_argument('--node',default=os.environ.get('NODE_BINARY','node'))
    p.add_argument('--inkscape',default='inkscape')
    a=p.parse_args()
    if not a.chrome or not a.playwright:p.error('--chrome and --playwright (or their environment variables) are required')
    out=a.out.resolve()
    for d in ['palettes','graph','figures','evidence']:(out/d).mkdir(parents=True,exist_ok=True)
    def run(cmd,**kw):subprocess.run([str(c) for c in cmd],check=True,**kw)
    for palette in ['paper-clear','blue-neutral']:
        run([sys.executable,ROOT/'source/resolve_palette.py','--config',ROOT/'palettes/presets.json','--target','paper','--palette',palette,'--output',out/'palettes'/f'{palette}.json'])
    run([sys.executable,ROOT/'source/build.py','--input',a.input,'--out',out])
    env=dict(os.environ,CHROME_BINARY=a.chrome,PLAYWRIGHT_MODULE=a.playwright)
    for name,move in [('model','dense_attention'),('msa','index_queries'),('moe','shared_expert')]:
        for palette in ['paper-clear','blue-neutral']:
            cmd=[a.node,ROOT/'runtime/export.mjs','--input',out/'native'/f'{name}-{palette}.drawio','--out',out/'graph'/f'{name}-{palette}','--graph-js',a.graph_js,'--label-mode','plain']
            if palette=='paper-clear':cmd+=['--move',move]
            run(cmd,env=env)
    run([sys.executable,ROOT/'source/finish.py','--out',out,'--inkscape',a.inkscape])
    run([sys.executable,ROOT/'source/verify.py','--out',out])
    run([a.node,ROOT/'source/browser-qa.mjs','--out',out,'--chrome',a.chrome],env=env)

if __name__=='__main__':main()
