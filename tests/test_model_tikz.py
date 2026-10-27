import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('model_tikz_renderer', ROOT / 'tools/render_model_tikz.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
SOURCE = r'''\documentclass[border=4pt]{standalone}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
\node[draw] (a) {Input};
\node[draw] (b) at (2,0) {Output};
\draw[->] (a) -- (b);
\end{tikzpicture}
\end{document}
'''


class TikzModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'authored.tex'
        self.source.write_text(SOURCE)
        self.output = self.root / 'rendered'

    def ready(self, engine, info, env=None):
        return {'ready': True, 'missing': [], 'engine': engine}, {
            name: '/mock/' + name for name in [engine, 'kpsewhich', 'pdfinfo', 'pdftocairo', 'pdftoppm']}

    def fake_run(self, argv, cwd, env, timeout):
        self.assertNotIn('SECRET_TEST', env)
        self.assertEqual(env['openin_any'], 'p')
        self.assertEqual(env['openout_any'], 'p')
        self.assertEqual(env['shell_escape'], 'f')
        name = Path(argv[0]).name
        work = Path(cwd)
        if argv[1:] in (['--version'], ['-v']):
            return name + ' test version\n'
        if name in ('pdflatex', 'xelatex'):
            self.assertIn('-no-shell-escape', argv)
            self.assertIn('-halt-on-error', argv)
            (work / 'figure.pdf').write_bytes(b'%PDF-1.5\nmock\n')
        elif name == 'pdfinfo':
            return 'Pages: 1\n'
        elif name == 'pdftocairo':
            (work / 'figure.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0 L1 1"/></svg>')
        elif name == 'pdftoppm':
            (work / 'figure.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 8 + struct.pack('>II', 20, 10))
        return ''

    def test_source_and_engine_selection(self):
        info = renderer.validate_source(SOURCE)
        self.assertEqual(renderer.choose_engine('auto', info), 'pdflatex')
        fonts = renderer.validate_source(SOURCE.replace('{tikz}', '{tikz,fontspec}'))
        self.assertEqual(renderer.choose_engine('auto', fonts), 'xelatex')
        with self.assertRaises(ValueError):
            renderer.choose_engine('pdflatex', fonts)

    def test_requires_explicit_trust_before_render(self):
        with self.assertRaisesRegex(ValueError, 'trusted-source'):
            renderer.render(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_file_shell_macro_and_character_escape_directives(self):
        for command in [r'\input{secret}', r'\includegraphics{photo}', r'\write18{cmd}',
                        r'\openin1=secret', r'\openout1=secret', r'\directlua{os.execute("cmd")}',
                        r'\csname input\endcsname', r'\catcode1=2', r'\def\x{hello}',
                        r'\special{file:secret}', r'\pdfobj file{secret}', '^^5cinput',
                        r'\begin{filecontents}{out}text\end{filecontents}']:
            with self.subTest(command=command), self.assertRaises(ValueError):
                renderer.validate_source(SOURCE.replace(r'\end{document}', command + '\n' + r'\end{document}'))

    def test_rejects_unsupported_packages_libraries_and_resources(self):
        for text in [SOURCE.replace('{tikz}', '{../../secret}'),
                     SOURCE.replace('{tikz}', '{tikz,shellesc}'),
                     SOURCE.replace(r'\begin{document}', r'\usetikzlibrary{../../secret}\begin{document}'),
                     SOURCE.replace(r'\begin{document}', r'\setmainfont{/private/file}\begin{document}'),
                     SOURCE.replace(r'\begin{document}', r'\setmainfont{Font}[Path=/private/]\begin{document}')]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                renderer.validate_source(text)

    def test_rejects_malformed_and_oversize_source(self):
        for text in ['', '\x00', SOURCE.replace(r'\end{document}', ''), SOURCE + 'x' * (1024 * 1024)]:
            with self.assertRaises(ValueError):
                renderer.validate_source(text)

    def test_symlink_and_existing_output_are_not_overwritten(self):
        link = self.root / 'linked.tex'
        link.symlink_to(self.source)
        with self.assertRaises(ValueError):
            renderer.render(link, self.output, trusted_source=True)
        self.output.mkdir()
        kept = self.output / 'user.txt'
        kept.write_text('keep')
        with self.assertRaises(ValueError):
            renderer.render(self.source, self.output, trusted_source=True)
        self.assertEqual(kept.read_text(), 'keep')

    def test_bad_timeout(self):
        for value in [0, -1, 181, float('nan')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                renderer.render(self.source, self.output, timeout=value, trusted_source=True)

    def test_missing_dependencies_do_not_claim_render(self):
        missing = ({'ready': False, 'missing': ['xelatex.fmt'], 'engine': 'xelatex'}, {})
        with mock.patch.object(renderer, 'dependency_report', return_value=missing):
            with self.assertRaisesRegex(RuntimeError, 'xelatex.fmt'):
                renderer.render(self.source, self.output, engine='xelatex', trusted_source=True)
        self.assertFalse(self.output.exists())

    def test_explicit_dependency_configuration_and_minimal_environment(self):
        with mock.patch.dict(os.environ, {'SECRET_TEST': 'do-not-forward'}, clear=False):
            env = renderer.dependency_environment([self.root], self.root)
        self.assertNotIn('SECRET_TEST', env)
        self.assertEqual(env['TEXMF'], str(self.root))
        self.assertEqual(env['TEXFORMATS'], str(self.root))
        with self.assertRaises(ValueError):
            renderer.dependency_environment(['relative'])

    def test_mocked_conversion_artifact_hashes_and_semantic_boundary(self):
        semantic = self.root / 'source.drawio'
        semantic.write_text('<mxfile/>')
        with mock.patch.object(renderer, 'dependency_report', side_effect=self.ready), \
             mock.patch.object(renderer, 'run_command', side_effect=self.fake_run):
            result = renderer.render(self.source, self.output, trusted_source=True, semantic_source=semantic)
        self.assertEqual(result['status'], 'rendered')
        self.assertEqual(result['language_qa'], 'not_run')
        self.assertEqual(result['visual_qa'], 'not_run')
        self.assertIn('not verified', result['semantic_source']['status'])
        self.assertEqual(result['semantic_source']['sha256'], hashlib.sha256(semantic.read_bytes()).hexdigest())
        self.assertEqual(result['measurements']['png_width'], 20)
        self.assertEqual(set(result['artifacts']), {'figure.tex', 'figure.pdf', 'figure.svg', 'figure.png'})
        for name, record in result['artifacts'].items():
            self.assertEqual(record['sha256'], hashlib.sha256((self.output / name).read_bytes()).hexdigest())
        self.assertNotIn(str(self.root), (self.output / 'render-qa.json').read_text())

    def test_auto_uses_available_xelatex_format(self):
        def probe(engine, info, env=None):
            if engine == 'pdflatex':
                return {'ready': False, 'missing': ['pdflatex.fmt'], 'engine': engine}, {}
            return self.ready(engine, info, env)
        with mock.patch.object(renderer, 'dependency_report', side_effect=probe), \
             mock.patch.object(renderer, 'run_command', side_effect=self.fake_run):
            self.assertEqual(renderer.render(self.source, self.output, trusted_source=True)['engine'], 'xelatex')

    def test_multiple_pages_rejected(self):
        def two_pages(argv, cwd, env, timeout):
            if Path(argv[0]).name == 'pdfinfo' and argv[1:] == ['figure.pdf']:
                return 'Pages: 2\n'
            return self.fake_run(argv, cwd, env, timeout)
        with mock.patch.object(renderer, 'dependency_report', side_effect=self.ready), \
             mock.patch.object(renderer, 'run_command', side_effect=two_pages):
            with self.assertRaisesRegex(ValueError, 'one PDF page'):
                renderer.render(self.source, self.output, trusted_source=True)
        self.assertFalse(self.output.exists())

    def test_timeout_terminates_process_group(self):
        with self.assertRaises(TimeoutError):
            renderer.run_command([sys.executable, '-c', 'import time; time.sleep(5)'], self.root,
                                 {'PATH': os.environ.get('PATH', '')}, .05)

    def test_actual_smoke_when_dependencies_available(self):
        info = renderer.validate_source(SOURCE)
        ready, _ = renderer.dependency_report('xelatex', info, renderer.dependency_environment())
        if not ready['ready']:
            self.skipTest('Actual TeX/Poppler dependencies unavailable: ' + ', '.join(ready['missing']))
        result = renderer.render(self.source, self.output, engine='xelatex', timeout=60, trusted_source=True)
        self.assertEqual(result['page_count'], 1)
        self.assertGreater(result['artifacts']['figure.pdf']['bytes'], 100)
        self.assertGreater(result['measurements']['svg_path_elements'], 0)


if __name__ == '__main__':
    unittest.main()
