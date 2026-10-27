#!/usr/bin/env python3
"""Run Inkscape on engine SVGs; package the unchanged geometry in an offline HTML.

The final SVGs are Inkscape round trips of official Graph exports. This script
does not draw paths or substitute handwritten SVG geometry for an engine.
"""
from pathlib import Path
import argparse, json, re, subprocess, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)

def run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True)
    return dict(command=cmd,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)

def inline_svg(path,prefix):
    root=ET.parse(path).getroot()
    # IDs in six inline Inkscape SVGs must be unique at HTML document scope.
    oldids={e.attrib['id']:prefix+'-'+e.attrib['id'] for e in root.iter() if 'id' in e.attrib}
    for e in root.iter():
        for k,v in list(e.attrib.items()):
            if k=='id':e.set(k,oldids[v])
            else:
                for old,new in oldids.items():
                    v=v.replace('url(#'+old+')','url(#'+new+')')
                    if v=='#'+old:v='#'+new
                e.set(k,v)
    root.set('role','img');root.set('aria-label',{'model':'MiniMax M3.1-Flash vertical model architecture','msa':'MiniMax Sparse Attention mechanism','moe':'Mixture of Experts mechanism'}[prefix.split('-')[0]])
    # Keep native editable text and vector objects; intrinsic dimensions and viewBox
    # are retained while CSS sizes the whole figure proportionally.
    return ET.tostring(root,encoding='unicode')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT)
    ap.add_argument('--inkscape',default='inkscape')
    a=ap.parse_args();out=a.out.resolve();(out/'figures').mkdir(exist_ok=True)
    records=[]
    for name in ['model','msa','moe']:
        for palette in ['paper-clear','blue-neutral']:
            key=f'{name}-{palette}'; src=out/'graph'/f'{key}.svg'; dst=out/'figures'/f'{key}.svg'
            r=run([a.inkscape,str(src),'--export-plain-svg',f'--export-filename={dst}'])
            records.append(r)
            if r['returncode']:raise SystemExit(json.dumps(r))
            r=run([a.inkscape,str(dst),'--export-type=png',f'--export-filename={out/"figures"/(key+".png")}','--export-dpi=96'])
            records.append(r)
            if r['returncode']:raise SystemExit(json.dumps(r))
            r=run([a.inkscape,str(dst),'--query-all']); records.append(r)
            (out/'evidence'/f'{key}.inkscape-bounds.csv').write_text(r['stdout'])
    (out/'evidence/inkscape-commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    parts=[]
    for name,heading,desc in [
        ('model','模型主干','60 层 decoder；0–2 层为 dense FFN，3–59 层为 MoE。加法结点与 identity 残差均显式表示。'),
        ('msa','A · MiniMax Sparse Attention','索引器选择块；内容注意力在选中的 group-specific K/V 上进行精确计算。'),
        ('moe','B · Mixture of Experts','选择 bias 与混合权重分开；shared expert 在 routed ×2 之后相加。')]:
        fig=''.join(f'<div class="art {p}">{inline_svg(out/"figures"/f"{name}-{p}.svg",name+"-"+p)}</div>' for p in ['paper-clear','blue-neutral'])
        parts.append(f'<section id="{name}"><h2>{heading}</h2><p class="caption">{desc}</p><figure class="{name}">{fig}</figure></section>')
    html='''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MiniMax M3.1-Flash · Architecture</title><style>
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f7f9;color:#28343d;font:16px/1.6 Arial,"Noto Sans CJK SC",sans-serif}header{max-width:1180px;margin:36px auto 20px;padding:0 28px}h1{font-size:30px;margin:0 0 6px}header p{margin:0;color:#657581}.controls{max-width:1180px;margin:0 auto 24px;padding:16px 28px;background:white;border:1px solid #d7e0e7;border-radius:12px}.controls label{display:inline-block;padding:6px 14px;margin-right:12px;cursor:pointer;border-radius:20px}input[type=radio]{position:absolute;left:-9999px}#clear:checked~.controls label[for=clear],#neutral:checked~.controls label[for=neutral]{background:#e6eff7;font-weight:bold}nav{display:inline-flex;gap:18px;float:right;padding:6px 0}a{color:#38698f}main{max-width:1180px;margin:auto;padding:0 20px}section{background:#fff;margin:0 0 32px;border:1px solid #d7e0e7;border-radius:14px;padding:22px 24px;scroll-margin-top:20px}h2{font-size:22px;margin:0 0 4px}.caption{color:#657581;margin:0 0 14px}figure{margin:0 auto;max-width:100%}figure.model{max-width:870px}.art svg{display:block;width:100%;height:auto;background:white}.art.blue-neutral{display:none}#neutral:checked~main .paper-clear{display:none}#neutral:checked~main .blue-neutral{display:block}footer{max-width:1180px;margin:28px auto 44px;padding:0 28px;font-size:14px;color:#657581}footer p{margin:5px 0}@media(max-width:700px){header{padding:0 18px}h1{font-size:24px}.controls{margin:0 12px 18px;padding:12px}nav{float:none;display:flex;padding-top:10px}main{padding:0 10px}section{padding:14px 8px}h2,.caption{padding:0 8px}.caption{font-size:14px}footer{padding:0 18px}}@media print{body{background:white}.controls,header p{display:none}section{border:none;padding:0;break-after:page}header{margin:0}figure.model{max-width:100%}}
</style></head><body>
<header><h1>MiniMax M3.1-Flash</h1><p>论文级架构视图 · 英文技术标注 · 两套配色共用同一结构</p></header>
<input type="radio" name="palette" id="clear" checked><input type="radio" name="palette" id="neutral">
<div class="controls" role="group" aria-label="配色"><label for="clear">清彩论文</label><label for="neutral">素雅灰蓝</label><nav><a href="#model">模型</a><a href="#msa">MSA</a><a href="#moe">MoE</a></nav></div>
<main>'''+''.join(parts)+'''</main>
<footer><p>范围：省略 vision frontend、DSpark draft 内部和 training losses。DSpark 不计入60 层 decoder。</p>
<p>依据：固定模型配置 <a href="https://huggingface.co/MiniMaxAI/MiniMax-M3.1-Flash/blob/54e4e69dfc452b1e94a426c24a4fdeeaa8e3ad5e/config.json">54e4e69d</a>、提供的 SGLang 源码快照与 technical-facts.json。MSA 算法约束按提供的事实绘制；完整论文不在本次本地原始材料中。</p>
<p>母版为原生 draw.io；当前展示为官方 Graph 导出后经 Inkscape 导出的 SVG。配色控件使用 CSS，无需 JavaScript 或网络。</p></footer>
</body></html>'''
    (out/'minimax-m31-flash.html').write_text(html)
    print(json.dumps({'inkscape_export_commands':len(records),'html':'minimax-m31-flash.html'}))

if __name__=='__main__':main()
