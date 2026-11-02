"""QA only: render native PPTX directly to PNG, never an export input."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'libreoffice-qa'
UP=ROOT.parent/'FigGenie-paper-diagram-skill'
OUT.mkdir(exist_ok=True)
fonts=OUT/'fonts.conf'
fonts.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig><dir>/System/Library/Fonts</dir><dir>/Library/Fonts</dir><cachedir>/tmp/figgenie-lo-fontcache</cachedir><config></config></fontconfig>')
env={**os.environ,'FONTCONFIG_FILE':str(fonts)}
records=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd):
 p=subprocess.run(list(map(str,cmd)),env=env,text=True,capture_output=True)
 records.append({'command':list(map(str,cmd)),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)

def render(source,name):
 dest=OUT/name;dest.mkdir(exist_ok=False)
 cmd=['soffice','--headless','--convert-to','png:impress_png_Export:{"PixelWidth":{"type":"long","value":"1800"},"PixelHeight":{"type":"long","value":"990"}}','--outdir',dest,source]
 before=sha(source);run(cmd);assert before==sha(source)
 png=dest/(source.stem+'.png');assert png.is_file()
 records[-1].update({'source_sha256':before,'png_sha256':sha(png),'visual_review':'not_run'})
try:
 for case in ('ascend-workflow','kv-offload'):
  for mode in ('pptx','both'):
   render(OUT.parent/'accepted-modes'/case/mode/'fig.pptx',case+'-'+mode+'-system-fonts')
  raw=OUT/(case+'-raw');raw.mkdir(exist_ok=False)
  run([sys.executable,UP/'skills/figgenie-paper-diagram/scripts/svg2pptx.py',ROOT/'examples/figgenie'/case/'fig.svg','--spec',ROOT/'examples/figgenie'/case/'spec.json','-o',raw/'fig.pptx'])
  render(raw/'fig.pptx',case+'-before-shadow-fix')
 render(OUT.parent/'long-label-export/fig.pptx','long-label-system-fonts')
finally:
 (OUT/'commands.json').write_text(json.dumps({'renderer':subprocess.check_output(['soffice','--version'],text=True).strip(),'environment':{'FONTCONFIG_FILE':str(fonts)},'purpose':'QA-only PPTX to PNG; never used as a source for final SVG, PNG or PPTX','commands':records},ensure_ascii=False,indent=2)+'\n')
