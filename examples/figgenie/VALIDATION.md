# FigGenie native-vector fixtures: actual validation

These two fixtures each have one technical brief, one design plan and one canonical SVG. They are **not** three independent Skill comparison runs. All source geometry is in `fig.svg`; `spec.json` carries semantics, not another coordinate model. The Ascend revision is an explicit later label edit, not a second export design.

Upstream checkout tested: `c136a6aeefc6f6fe11fc615a5199cca57be3322a`.

## Actual results

- Both `spec_validate.py spec.json`: 0 errors. Deliberate warning: 330 pt presentation height exceeds the paper double-column 313 pt p95. The example uses 11 pt presentation labels, not a paper-size font mechanically scaled.
- Both `svg2pptx.py fig.svg --spec spec.json -o fig.pptx` and `pptx_check.py fig.pptx --svg fig.svg`: passed. ZIP inspection confirms native text, shapes, groups, connectors/freeforms; zero picture objects. See logs and `validation.json`.
- SVG previews: Inkscape rendering at 1800 px, actually viewed. Layout, labels, branch/feedback direction and KV readiness path checked.
- PPT previews: actual `soffice --headless --convert-to pdf` followed by `pdftoppm`, actually viewed. This PDF is **QA-only**, never an output source or image-to-PPT conversion. Labels, main routes and branch states remain present. The generated deck is editable native objects, not a raster background.
- The PPT renderer adds visible theme shadows absent from SVG, despite upstream `no_shadow`; thus **pixel-level visual equivalence is not passed**. Content and geometry are readable, but final native PowerPoint appearance remains `not_run`.
- A first draft's multiline `<tspan>` label with no parent `x/y` became visually blank in PPT despite inventory passing. Fixed **in the canonical SVG** by using separate native `<text>` elements, then exported and rendered again. This is why inventory pass is not a visual pass.
- SVG TeX Gyre Heros is mapped by the upstream PPT exporter to Arial (and Microsoft YaHei CJK default). Font substitution is explicit. No formulas are present; OMML validation is `not_run` / not applicable.

## Required browser check is blocked, not passed

Actual native `check.py fig.svg --spec spec.json` cannot complete: this environment lacks the Playwright-managed Chromium binary. A temporary `PLAYWRIGHT_BROWSERS_PATH` adapter pointing at installed `/usr/bin/chromium` was tried; Chromium fails `socket() Operation not permitted`. A requested escalated run failed before execution due to the environment's bwrap read-only mount setup. No upstream scripts or security settings were modified. Therefore browser-rendering and native lint are **blocked**, not zero-error or passed.

All six actual thin-wrapper runs (two examples × `image`, `pptx`, `both`) were attempted. They correctly fail closed at this native check. Their manifests record the same source hash across each example's three modes and zero design invocations, but **no mode is claimed end-to-end successful**. Direct diagnostic exports and Inkscape QA above are not a production bypass.

Re-run on a supported host with Playwright Chromium available:

```sh
python skills/technical-architecture-diagrams/scripts/figgenie_export.py \
  examples/figgenie/ascend-workflow/fig.svg \
  --spec examples/figgenie/ascend-workflow/spec.json \
  --upstream /path/to/pinned/FigGenie-paper-diagram-skill \
  --out /new/output/directory --output-format both --display-intent presentation
```

Repeat for each example and each mode, using a fresh output directory. Inspect the generated browser PNG and an actual PPT rendering before acceptance. Do not overwrite manual edits.

## Long-label revision

`ascend-workflow/revision/` changes only `n:vector` to “Generate Vector / from workload”, with brief/spec version 2 and the same stable group IDs. All unrelated group XML is byte-equivalent under the XML serializer; edge geometry and endpoints remain unchanged because the longer two-line label fits inside the existing node. `stability.json` records old/new hashes. The revision's native PPT check and both Inkscape/LibreOffice visual inspections passed for content and geometry. Browser check remains blocked. Nothing was edited directly in a generated PPTX.

## Scope and provenance

The figures are conceptual validation examples, not a claim about a particular Ascend kernel commit or measured speedup. User-requested C+V workflow and generic KV residency dependencies are explicitly bounded in the briefs. Two upstream exemplar images were inspected in the installed checkout for layout ideas; no exemplar image or font source asset was copied. Embedded SVG font subsets are upstream-produced output artifacts, not a vendored font library.
