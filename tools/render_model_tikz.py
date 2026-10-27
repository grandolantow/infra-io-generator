#!/usr/bin/env python3
"""Render reviewed, self-contained TikZ through real TeX/Poppler tools.

This is a restricted workflow, NOT a security sandbox for arbitrary TeX. The
caller must review the source and explicitly pass --trusted-source. No source
translation, architecture generation or scientific/language QA is performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import tempfile
import time
from xml.etree import ElementTree as ET

PACKAGES = frozenset({'tikz', 'xcolor', 'amsmath', 'amssymb', 'fontspec', 'xeCJK'})
CLASSES = frozenset({'standalone', 'article'})
LIBRARIES = frozenset({'arrows', 'arrows.meta', 'positioning', 'calc', 'fit',
                       'backgrounds', 'matrix', 'shapes', 'shapes.geometric',
                       'shapes.symbols', 'patterns', 'decorations.pathreplacing'})
FORBIDDEN = re.compile(r'\\(?:input|include|includeonly|includegraphics|openin|openout|read|readline|write|immediate|special|catcode|csname|endcsname|expandafter|scantokens|directlua|latelua|luaexec|def|gdef|edef|xdef|let|futurelet|newcommand|renewcommand|providecommand|newenvironment|renewenvironment|everyjob|everypar|toks|loop|repeat|use|RequirePackage|LoadClass|pdf[a-zA-Z]*|XeTeX[a-zA-Z]*)(?![A-Za-z])')


def validate_source(text):
    """Conservative source gate; does not prove arbitrary TeX harmless."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('A nonempty UTF-8 TeX source is required')
    if len(text.encode('utf-8')) > 1024 * 1024:
        raise ValueError('TeX source exceeds the 1 MiB limit')
    # TeX ^^ encoding can turn innocent-looking bytes into control sequences.
    if '^^' in text or '\x00' in text:
        raise ValueError('TeX character-code escapes/NUL are not supported')
    clean = re.sub(r'(?<!\\)%[^\n]*', '', text)
    match = FORBIDDEN.search(clean)
    if match:
        raise ValueError('Unsupported TeX directive: ' + match.group(0))
    if re.search(r'\\begin\s*\{\s*filecontents\*?\s*\}', clean):
        raise ValueError('filecontents is not supported')
    classes = re.findall(r'\\documentclass(?:\[[^\]]*\])?\s*\{([^{}]+)\}', clean)
    if len(classes) != 1 or classes[0] not in CLASSES:
        raise ValueError('Use one literal standalone or article documentclass')
    packages = set()
    matches = list(re.finditer(r'\\usepackage(?:\[[^\]]*\])?\s*\{([^{}]+)\}', clean))
    if len(matches) != len(re.findall(r'\\usepackage\b', clean)):
        raise ValueError('Package declarations must be literal')
    for match in matches:
        names = {name.strip() for name in match.group(1).split(',')}
        if not names <= PACKAGES:
            raise ValueError('Unsupported package; only reviewed drawing packages are allowed')
        packages.update(names)
    if 'tikz' not in packages or not re.search(r'\\begin\s*\{tikzpicture\}', clean):
        raise ValueError('A tikz package and tikzpicture environment are required')
    libs = list(re.finditer(r'\\usetikzlibrary\s*\{([^{}]+)\}', clean))
    if len(libs) != len(re.findall(r'\\usetikzlibrary\b', clean)):
        raise ValueError('TikZ library declarations must be literal')
    for match in libs:
        if not {name.strip() for name in match.group(1).split(',')} <= LIBRARIES:
            raise ValueError('Unsupported TikZ library')
    if re.search(r'(?:Path|ExternalLocation)\s*=', clean, re.I):
        raise ValueError('External font/resource paths are not supported')
    for match in re.finditer(r'\\(?:setmainfont|setsansfont|setmonofont|setCJKmainfont)\s*\{([^{}]*)\}', clean):
        if '/' in match.group(1) or '\\' in match.group(1):
            raise ValueError('Font names cannot contain filesystem paths')
    if '\\begin{document}' not in clean or '\\end{document}' not in clean:
        raise ValueError('A complete self-contained document is required')
    return {'document_class': classes[0], 'packages': sorted(packages),
            'requires_xelatex': bool(packages & {'fontspec', 'xeCJK'})}


def choose_engine(requested, source_info):
    if requested not in ('auto', 'pdflatex', 'xelatex'):
        raise ValueError('Unsupported TeX engine')
    selected = ('xelatex' if source_info['requires_xelatex'] else 'pdflatex') if requested == 'auto' else requested
    if source_info['requires_xelatex'] and selected != 'xelatex':
        raise ValueError('fontspec/xeCJK sources require xelatex')
    return selected


def dependency_environment(texmf_roots=None, format_dir=None):
    env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    # Only TeX dependency search settings are inherited; arbitrary process secrets are not.
    for key in ['TEXMF', 'TEXFORMATS']:
        if key in os.environ:
            value = os.environ[key]
            if any(c in value for c in ('\n', '\r', '\x00')):
                raise ValueError('Invalid TeX dependency environment')
            env[key] = value
    roots = []
    for value in texmf_roots or []:
        path = Path(value)
        if not path.is_absolute() or path.is_symlink() or not path.is_dir():
            raise ValueError('texmf-root must be an existing absolute non-symlink directory')
        if any(c in str(path) for c in ('{', '}', ',', '\n', '\r', '\x00')):
            raise ValueError('Unsupported characters in texmf-root')
        roots.append(str(path))
    if roots:
        env['TEXMF'] = '{' + ','.join(roots) + '}' if len(roots) > 1 else roots[0]
    if format_dir is not None:
        path = Path(format_dir)
        if not path.is_absolute() or path.is_symlink() or not path.is_dir():
            raise ValueError('format-dir must be an existing absolute non-symlink directory')
        if any(c in str(path) for c in (':', '\n', '\r', '\x00')):
            raise ValueError('Unsupported characters in format-dir')
        env['TEXFORMATS'] = str(path)
    return env


def dependency_report(engine, source_info, env=None):
    names = [engine, 'kpsewhich', 'pdfinfo', 'pdftocairo', 'pdftoppm']
    paths = {name: shutil.which(name) for name in names}
    missing = [name for name, path in paths.items() if not path]
    resources = [engine + '.fmt', source_info['document_class'] + '.cls',
                 *[p + '.sty' for p in source_info['packages']]]
    if paths['kpsewhich']:
        for resource in resources:
            try:
                result = subprocess.run([paths['kpsewhich'], resource], capture_output=True,
                                        text=True, timeout=5, check=False, env=env)
            except (OSError, subprocess.TimeoutExpired):
                missing.append(resource)
                continue
            if result.returncode or not result.stdout.strip():
                missing.append(resource)
    else:
        missing.extend(resources)
    return {'ready': not missing, 'missing': sorted(set(missing)), 'engine': engine}, paths


def run_command(argv, cwd, env, timeout):
    """Run without a shell and terminate the whole process group on timeout."""
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        stdout, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        raise TimeoutError('Renderer command exceeded the remaining time budget') from None
    if proc.returncode:
        raise RuntimeError(f'{Path(argv[0]).name} failed with exit code {proc.returncode}')
    return stdout


def inspect_outputs(work):
    svg = ET.parse(work / 'figure.svg').getroot()
    if svg.tag.split('}')[-1] != 'svg':
        raise ValueError('Converter did not produce SVG')
    forbidden = {'script', 'foreignObject', 'image'}
    if any(e.tag.split('}')[-1] in forbidden for e in svg.iter()):
        raise ValueError('Unexpected active or raster content in converted SVG')
    raw = (work / 'figure.png').read_bytes()
    if len(raw) < 24 or raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Converter did not produce PNG')
    width, height = struct.unpack('>II', raw[16:24])
    if not width or not height:
        raise ValueError('PNG has invalid dimensions')
    return {'png_width': width, 'png_height': height,
            'svg_text_elements': sum(e.tag.split('}')[-1] == 'text' for e in svg.iter()),
            'svg_path_elements': sum(e.tag.split('}')[-1] == 'path' for e in svg.iter()),
            'editability': 'TeX source is editable; converted glyph paths are not SVG text.'}


def render(input_path, out_dir, engine='auto', timeout=60, trusted_source=False, texmf_roots=None, format_dir=None, semantic_source=None):
    if not trusted_source:
        raise ValueError('Review the authored source and pass --trusted-source; arbitrary TeX is not sandboxed')
    if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 180:
        raise ValueError('timeout must be between 1 and 180 seconds')
    source = Path(input_path)
    if source.is_symlink() or not source.is_file() or source.suffix.lower() != '.tex':
        raise ValueError('input must be a regular .tex file, not a symlink')
    if source.stat().st_size > 1024 * 1024:
        raise ValueError('TeX source exceeds the 1 MiB limit')
    raw = source.read_bytes()
    info = validate_source(raw.decode('utf-8'))
    selected = choose_engine(engine, info)
    output = Path(out_dir)
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError('out-dir must be a new or empty non-symlink directory')
    base_env = dependency_environment(texmf_roots, format_dir)
    dependencies, binaries = dependency_report(selected, info, base_env)
    if engine == 'auto' and selected == 'pdflatex' and not dependencies['ready']:
        alternative, alt_binaries = dependency_report('xelatex', info, base_env)
        if alternative['ready']:
            selected, dependencies, binaries = 'xelatex', alternative, alt_binaries
    semantic = None
    if semantic_source is not None:
        semantic_path = Path(semantic_source)
        if semantic_path.is_symlink() or not semantic_path.is_file():
            raise ValueError('semantic-source must be a regular non-symlink file')
        semantic = {'sha256': hashlib.sha256(semantic_path.read_bytes()).hexdigest(),
                    'status': 'reference_only; correspondence to TeX not verified'}
    if not dependencies['ready']:
        raise RuntimeError('Missing TeX/Poppler dependencies: ' + ', '.join(dependencies['missing']))
    deadline = time.monotonic() + timeout
    commands = []
    with tempfile.TemporaryDirectory(prefix='model-tikz-') as td:
        work = Path(td)
        (work / 'figure.tex').write_bytes(raw)
        for name in ['cache', 'config']:
            (work / name).mkdir()
        env = {**base_env, 'HOME': td,
               'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TMPDIR': td,
               'openin_any': 'p', 'openout_any': 'p', 'shell_escape': 'f',
               'TEXMFOUTPUT': td, 'TEXMFVAR': str(work / 'cache'),
               'TEXMFCONFIG': str(work / 'config'), 'XDG_CACHE_HOME': str(work / 'cache')}
        def execute(name, args):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Renderer exceeded the total time budget')
            commands.append([name, *args])
            return run_command([binaries[name], *args], work, env, remaining)
        versions = {}
        for name in [selected, 'pdfinfo', 'pdftocairo', 'pdftoppm']:
            text = execute(name, ['--version'] if name == selected else ['-v'])
            versions[name] = text.splitlines()[0] if text.splitlines() else 'version unavailable'
        execute(selected, ['-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
                           '-file-line-error', '-output-directory=.', 'figure.tex'])
        if not (work / 'figure.pdf').is_file() or not (work / 'figure.pdf').read_bytes().startswith(b'%PDF-'):
            raise ValueError('TeX did not produce a PDF')
        pdf_info = execute('pdfinfo', ['figure.pdf'])
        pages = re.search(r'^Pages:\s*(\d+)\s*$', pdf_info, re.M)
        if not pages or int(pages.group(1)) != 1:
            raise ValueError('Exactly one PDF page is required; split multi-page figures explicitly')
        execute('pdftocairo', ['-svg', 'figure.pdf', 'figure.svg'])
        execute('pdftoppm', ['-png', '-singlefile', '-r', '144', 'figure.pdf', 'figure'])
        measured = inspect_outputs(work)
        if output.is_symlink() or (output.exists() and any(output.iterdir())):
            raise ValueError('out-dir changed while rendering; refusing to overwrite')
        output.mkdir(parents=True, exist_ok=True)
        artifacts = {}
        for name in ['figure.tex', 'figure.pdf', 'figure.svg', 'figure.png']:
            data = (work / name).read_bytes()
            with (output / name).open('xb') as handle:
                handle.write(data)
            artifacts[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        report = {'schema_version': 1, 'renderer': 'tikz-tex-poppler', 'status': 'rendered',
                  'engine': selected, 'tool_versions': versions, 'semantic_source': semantic,
                  'dependency_configuration': {'custom_texmf': bool(texmf_roots), 'custom_format_dir': format_dir is not None, 'inherited_tex_search_settings': any(k in os.environ for k in ['TEXMF', 'TEXFORMATS'])}, 'input_sha256': hashlib.sha256(raw).hexdigest(),
                  'page_count': 1, 'commands': commands, 'artifacts': artifacts,
                  'measurements': measured, 'language_qa': 'not_run', 'visual_qa': 'not_run',
                  'limits': ['Reviewed self-contained source only; not a sandbox for arbitrary TeX.',
                             'No semantic correctness or source-language compliance is inferred.',
                             'No Chromium, network download, or automatic package installation is used.']}
        (output / 'render-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    parser.add_argument('--engine', choices=['auto', 'pdflatex', 'xelatex'], default='auto')
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--trusted-source', action='store_true')
    parser.add_argument('--texmf-root', type=Path, action='append', help='Repeat for reviewed existing TeX distribution roots; no packages are installed')
    parser.add_argument('--format-dir', type=Path, help='Existing reviewed engine format directory')
    parser.add_argument('--semantic-source', type=Path, help='Hash a separately checked semantic source; does not assert correspondence to TeX')
    args = parser.parse_args()
    try:
        report = render(args.input, args.out_dir, args.engine, args.timeout, args.trusted_source, args.texmf_root, args.format_dir, args.semantic_source)
    except (OSError, UnicodeError, ValueError, RuntimeError, TimeoutError) as exc:
        parser.exit(2, f'Render blocked: {exc}\n')
    print(json.dumps({'status': report['status'], 'engine': report['engine'],
                      'page_count': report['page_count'], 'visual_qa': report['visual_qa']}, indent=2))


if __name__ == '__main__':
    main()
