#!/usr/bin/env python3
"""Render checked-in native examples via official Graph, then Inkscape."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/technical-architecture-diagrams'


def run(args):
    result = subprocess.run([str(x) for x in args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(str(args[0]) + ' failed:\n' + (result.stderr or result.stdout)[-3500:])
    return result.stdout


def chrome_path(explicit):
    if explicit or os.environ.get('CHROME_BINARY'):
        return explicit or os.environ['CHROME_BINARY']
    # Find the browser associated with the installed Playwright dependency.
    code = "const p=await import(process.env.PLAYWRIGHT_MODULE||'playwright');console.log(p.chromium.executablePath())"
    return run(['node', '--input-type=module', '-e', code]).strip()


def finish(source, master, output):
    from lxml import etree as E
    from PIL import Image
    root = E.parse(str(source)).getroot()
    for node in root.iter():
        if 'light-dark(' in node.get('style', ''):
            del node.attrib['style']
        if E.QName(node).localname == 'path':
            node.set('stroke-linejoin', 'round')
            node.set('stroke-linecap', 'round')
    meta = E.SubElement(root, '{http://www.w3.org/2000/svg}metadata')
    meta.text = json.dumps({'master': master.name, 'master_sha256': hashlib.sha256(master.read_bytes()).hexdigest(),
                            'finish': ['round joins/caps', 'concrete light colors'], 'bidirectional_sync': False})
    stage = output.with_name(output.stem + '_stage.svg')
    E.ElementTree(root).write(str(stage), encoding='UTF-8', xml_declaration=True)
    run(['inkscape', stage, '--export-type=svg', '--export-filename=' + str(output)])
    png = output.with_suffix('.png')
    temporary = png.with_name(png.stem + '_tmp.png')
    run(['inkscape', output, '--export-type=png', '--export-filename=' + str(temporary)])
    with Image.open(temporary) as im:
        im.load()
    os.replace(temporary, png)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--example', choices=['minimax', 'attnres'], required=True)
    ap.add_argument('--palette', choices=['paper-clear', 'blue-neutral'], default='paper-clear',
                    help='MiniMax palette; Attention Residuals preserves its calibrated historical colors')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--chrome')
    ap.add_argument('--move', help='Optional native cell ID for a mouse-drag probe')
    a = ap.parse_args()
    out = a.out.resolve()
    if out == ROOT or out.is_relative_to(SKILL) or SKILL.is_relative_to(out):
        ap.error('Use a task output directory outside the installed Skill')
    out.mkdir(parents=True, exist_ok=True)
    if a.example == 'attnres':
        if a.palette != 'paper-clear':
            ap.error('AttnRes sample keeps calibrated historical colors; palette switching is demonstrated by MiniMax')
        run(['python3', SKILL / 'assets/golden-refined/build.py', '--out', out])
        masters = [out / 'attnres_refined.drawio']
    else:
        source = ROOT / 'examples/minimax-m31' / a.palette
        masters = []
        for name in ['portrait', 'detail']:
            master = out / (name + '.drawio')
            shutil.copyfile(source / master.name, master)
            masters.append(master)
        shutil.copyfile(ROOT / 'examples/minimax-m31/facts.json', out / 'facts.json')
    browser = chrome_path(a.chrome)
    checks = []
    for master in masters:
        prefix = out / ('attnres_drawio' if a.example == 'attnres' else master.stem + '_drawio')
        args = ['node', SKILL / 'scripts/drawio_runtime/export.mjs', '--input', master,
                '--out', prefix, '--chrome', browser, '--graph-js', ROOT / 'third_party/drawio/app.min.js']
        if a.move and (a.example == 'attnres' or master.stem == 'portrait'):
            args.extend(['--move', a.move])
        run(args)
        final = out / (master.stem + '_final.svg')
        finish(prefix.with_suffix('.svg'), master, final)
        qa = json.loads(prefix.with_suffix('.runtime-qa.json').read_text())
        checks.append({'figure': master.stem, 'canvas': qa['canvas'], 'metrics': qa['native_shape_metrics'],
                       'javascript_errors': qa['javascript_errors'], 'edit_probe': qa.get('edit_test', {}).get('moved', 'not_run')})
    if a.example == 'attnres':
        run(['python3', SKILL / 'assets/golden-refined/verify.py', out])
    summary = {'example': a.example, 'palette': a.palette if a.example == 'minimax' else 'historical-golden',
               'renderer': 'official draw.io Graph + Inkscape CLI', 'checks': checks,
               'not_run': ['draw.io Desktop/EditorUi', 'PPTX edit', 'user preference evaluation']}
    (out / 'render-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(str(exc))
