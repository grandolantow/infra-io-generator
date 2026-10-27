# Authored TikZ model rendering

Use the existing TikZ backend when a reviewed, self-contained TeX drawing is the chosen model-diagram source. This is a renderer, not a model parser or a substitute for the model Skill's factual/structural design. Do not relabel a model-specific golden template as another model.

```sh
python tools/render_model_tikz.py --input authored-model.tex --out-dir build/model --engine xelatex --timeout 60 --trusted-source
```

The CLI lives at the repository root, not inside a standalone copied Skill. Install a working TeX distribution with the needed format/classes/packages (including TikZ), plus `pdfinfo`, `pdftocairo` and `pdftoppm`. A TeX binary alone is insufficient. Configure existing runtime search paths with repeated `--texmf-root ROOT` and `--format-dir DIR`, or the inherited `TEXMF` / `TEXFORMATS` environment settings; do not hardcode another machine's paths or silently install dependencies.

## Trust and execution limits

- `--trusted-source` is explicit acknowledgment that the source is task-authored/reviewed and self-contained; it is not a permission to execute arbitrary downloaded TeX.
- The wrapper rejects specified unsafe directives/packages, disables shell escape, uses an isolated temporary working directory, constrains file access and bounds subprocess execution. These are defense-in-depth measures, **not a complete TeX sandbox or a proof that arbitrary TeX is safe**.
- No Chromium/JavaScript execution is involved. Do not use this path to relaunch a blocked browser or conceal an unexecuted backend.
- Missing dependencies, invalid input or rendering failures are errors, not a successful SVG fallback. Never replace engine output with a handwritten SVG while claiming this renderer ran.

## Outputs and verification

Outputs are `figure.tex`, `figure.pdf`, `figure.svg`, `figure.png` and `render-qa.json`. The wrapper checks actual PDF page count and SVG/PNG structure/dimensions. Commands and content hashes identify what ran; these checks do not establish scientific accuracy, layout quality or language correctness.

TeX is the editable source. PDF/SVG glyph outlines are not editable SVG text, and a rendered figure is not an editable draw.io mother graph. Preserve the reviewed structural/fact source separately. With `--semantic-source`, its hash is recorded; that does **not** prove that the TeX labels/edges match it.

## Language and semantic linkage

The model workflow also uses `diagram-en-prose-zh`: English diagram-integrated labels/short annotations, Chinese standalone explanatory prose, source terms/symbols preserved. Apply `check_language.py` to the role-annotated draw.io or report source and record the role assignment/semantic review. Then compare the actual TeX and rendered labels against that source. The renderer does not parse arbitrary TeX into semantic roles, and must keep language QA as not_run rather than borrowing a pass from an unrelated source.

PPT adapters may call this CLI and consume its QA plus the shared language QA, but must preserve each input hash and the manual correspondence-review boundary. They must not implement a second renderer or language policy.
